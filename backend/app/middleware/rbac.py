"""
app/middleware/rbac.py
======================
FastAPI dependencies for Role-Based Access Control (RBAC).
"""

import time
from typing import Any, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rbac import TenantPermission, TenantRolePermission, TenantUserRole, TenantRole

# In-process TTL cache for RBAC checks. Every RequirePermission call ran two
# uncached DB queries (admin check + 4-join permission check); a page firing
# 6 API calls issued 12+ RBAC queries. RBAC assignments change rarely, so a
# short TTL trades a few seconds of staleness after a permission change for
# a large reduction in DB load on the hottest path in the app.
#
# This is single-process only — it does not stay consistent across multiple
# app workers/instances (each has its own cache, and one worker revoking a
# role doesn't invalidate another worker's cached "allowed" result until its
# entry expires). A correct multi-instance cache needs a shared store
# (Redis, now wired for Celery — see app/core/celery_app.py) with explicit
# invalidation on role/permission writes. That's a real follow-up, not done
# here: it would mean touching every RBAC mutation endpoint to invalidate
# on write, which is a larger change than this pass's scope.
_CACHE_TTL_SECONDS = 30
_permission_cache: dict[tuple, tuple[bool, float]] = {}


def _cache_get(key: tuple) -> bool | None:
    entry = _permission_cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if expires_at < time.monotonic():
        _permission_cache.pop(key, None)
        return None
    return value


def _cache_set(key: tuple, value: bool) -> None:
    _permission_cache[key] = (value, time.monotonic() + _CACHE_TTL_SECONDS)


def _clear_permission_cache() -> None:
    """Test-only: reset the cache between test runs."""
    _permission_cache.clear()


class RequirePermission:
    """
    Dependency class to enforce RBAC permissions on endpoints.

    Usage:
        @router.get("/")
        async def get_items(
            db: AsyncSession = Depends(get_db),
            _: bool = Depends(RequirePermission(module="Inventory", feature="Items", action="Read"))
        ):
            ...
    """
    def __init__(self, module: str, feature: str, action: str):
        self.module = module
        self.feature = feature
        self.action = action

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> bool:
        tenant_id: UUID | None = getattr(request.state, "tenant_id", None)
        user_id: UUID | None = getattr(request.state, "user_id", None)

        if not tenant_id or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User or tenant context missing"
            )

        admin_cache_key = ("admin", tenant_id, user_id)
        is_admin = _cache_get(admin_cache_key)
        if is_admin is None:
            # 1. Check for admin bypass — an immutable flag (TenantRole.is_admin_bypass),
            # not the role name. Keying this off name string ("Super Admin",
            # "Organization Admin") meant renaming either role silently broke
            # admin access, and any tenant admin with RBAC:Roles:Create could
            # self-escalate by creating a custom role with the same name — the
            # bypass check never looked at anything else. is_admin_bypass isn't
            # exposed by TenantRoleCreate/TenantRoleUpdate (see app/schemas/rbac.py),
            # so it can't be set via the public API.
            from app.models.users import UserProfile
            admin_stmt = (
                select(TenantRole.id, UserProfile.user_id, TenantUserRole.tenant_id)
                .join(TenantUserRole, TenantUserRole.role_id == TenantRole.id)
                .join(UserProfile, UserProfile.id == TenantUserRole.user_id)
                .where(
                    UserProfile.user_id == user_id,
                    TenantUserRole.tenant_id == tenant_id,
                    TenantRole.is_admin_bypass.is_(True),
                )
                .limit(1)
            )
            admin_result = await db.execute(admin_stmt)
            is_admin = admin_result.first() is not None
            _cache_set(admin_cache_key, is_admin)

        if is_admin:
            return True

        perm_cache_key = ("perm", tenant_id, user_id, self.module, self.feature, self.action)
        allowed = _cache_get(perm_cache_key)
        if allowed is None:
            from app.models.users import UserProfile
            # 2. Build query to check if user has the permission through any assigned role
            stmt = (
                select(TenantUserRole)
                .join(UserProfile, UserProfile.id == TenantUserRole.user_id)
                .join(TenantRole, TenantRole.id == TenantUserRole.role_id)
                .join(TenantRolePermission, TenantRolePermission.role_id == TenantRole.id)
                .join(TenantPermission, TenantPermission.id == TenantRolePermission.permission_id)
                .where(
                    UserProfile.user_id == user_id,
                    TenantUserRole.tenant_id == tenant_id,
                    TenantPermission.module == self.module,
                    TenantPermission.feature == self.feature,
                    TenantPermission.action == self.action,
                )
                .limit(1)
            )
            result = await db.execute(stmt)
            allowed = result.scalar_one_or_none() is not None
            _cache_set(perm_cache_key, allowed)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {self.action} on {self.module}.{self.feature}"
            )

        # Optional: In a full enterprise system, we would also check assignment.branch_id
        # against a requested branch_id parameter to ensure scoped access.

        return True
