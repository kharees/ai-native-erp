"""
app/middleware/rbac.py
======================
FastAPI dependencies for Role-Based Access Control (RBAC).
"""

from typing import Any, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rbac import TenantPermission, TenantRolePermission, TenantUserRole, TenantRole

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

        # 1. Check for Super Admin or Organization Admin bypass
        from app.models.users import UserProfile
        admin_stmt = (
            select(TenantRole.id, TenantRole.name, UserProfile.user_id, TenantUserRole.tenant_id)
            .join(TenantUserRole, TenantUserRole.role_id == TenantRole.id)
            .join(UserProfile, UserProfile.id == TenantUserRole.user_id)
            .where(
                UserProfile.user_id == user_id,
                TenantUserRole.tenant_id == tenant_id,
                TenantRole.name.in_(["Super Admin", "Organization Admin"])
            )
            .limit(1)
        )
        admin_result = await db.execute(admin_stmt)
        row = admin_result.first()
        if row:
            return True

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
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {self.action} on {self.module}.{self.feature}"
            )
            
        # Optional: In a full enterprise system, we would also check assignment.branch_id 
        # against a requested branch_id parameter to ensure scoped access.
            
        return True
