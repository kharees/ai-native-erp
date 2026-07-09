"""
tests/test_rbac.py
==================
Validates the RBAC dependency block (RequirePermission).
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, text

from app.models.tenants import Tenant
from app.models.users import UserProfile
from app.models.auth import UserAccount
from app.models.rbac import TenantRole, TenantPermission, TenantRolePermission, TenantUserRole
from app.middleware.rbac import RequirePermission

pytestmark = pytest.mark.asyncio

# tests/conftest.py's async_client fixture globally stubs RequirePermission.__call__
# to always return True (so other endpoint tests don't need full RBAC fixtures).
# These tests exist specifically to validate real permission enforcement, so they
# must restore the genuine implementation, captured here at import time before any
# fixture has a chance to monkeypatch it.
_real_require_permission_call = RequirePermission.__call__

async def setup_rbac_scenario(db: AsyncSession):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # 1. Tenant & User
    tenant = Tenant(id=tenant_id, name="RBAC Corp", slug="rbac", plan="free", company_info={}, business_settings={}, is_active=True, created_at=now, updated_at=now)
    db.add(tenant)
    db.add(UserAccount(id=user_id, email=f"{user_id}@test.local", hashed_password="not-a-real-hash", is_active=True, created_at=now, updated_at=now))
    # Several FKs below (e.g. TenantRole.tenant_id) are nullable, so SQLAlchemy's
    # dependency-based insert ordering won't guarantee correct order; flush per tier.
    await db.flush()

    up_id = uuid.uuid4()
    user_prof = UserProfile(
        id=up_id, user_id=user_id, tenant_id=tenant_id,
        first_name="Test User", preferences={}, status="Active", role="member", timezone="UTC", locale="en",
        is_active=True, created_at=now, updated_at=now
    )
    db.add(user_prof)

    # 2. Role
    role_id = uuid.uuid4()
    role = TenantRole(id=role_id, tenant_id=tenant_id, name="Inventory Admin", is_system=False, hierarchy_level=100, created_at=now, updated_at=now)
    db.add(role)

    # 3. Permission (Inventory -> Read)
    perm_id = uuid.uuid4()
    perm = TenantPermission(id=perm_id, module="Inventory", feature="Items", action="Read", created_at=now)
    db.add(perm)

    await db.flush()

    # 4. Bind Role -> Perm
    rp = TenantRolePermission(id=uuid.uuid4(), role_id=role_id, permission_id=perm_id, conditions={}, created_at=now)
    db.add(rp)

    # 5. Bind User -> Role
    ur = TenantUserRole(id=uuid.uuid4(), tenant_id=tenant_id, user_id=up_id, role_id=role_id, created_at=now)
    db.add(ur)

    await db.commit()
    return tenant_id, user_id

async def test_rbac_access_granted(async_client: AsyncClient, db_session: AsyncSession, mock_jwt):
    RequirePermission.__call__ = _real_require_permission_call
    tenant_id, user_id = await setup_rbac_scenario(db_session)
    token = mock_jwt(sub=str(user_id), tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}

    response = await async_client.get("/api/v1/rbac/roles", headers=headers)
    assert response.status_code == 403

async def test_rbac_super_admin_bypass(async_client: AsyncClient, db_session: AsyncSession, mock_jwt):
    RequirePermission.__call__ = _real_require_permission_call
    tenant_id, user_id = await setup_rbac_scenario(db_session)
    
    up_id = (await db_session.execute(select(UserProfile.id).where(UserProfile.user_id == user_id))).scalar()
    
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    role_id = uuid.uuid4()
    org_role = TenantRole(id=role_id, tenant_id=tenant_id, name="Organization Admin", is_system=False, hierarchy_level=100, created_at=now, updated_at=now)
    db_session.add(org_role)
    org_user_role = TenantUserRole(id=uuid.uuid4(), tenant_id=tenant_id, user_id=up_id, role_id=role_id, created_at=now)
    db_session.add(org_user_role)
    await db_session.flush()
    
    token = mock_jwt(sub=str(user_id), tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}
    
    response = await async_client.get("/api/v1/rbac/roles", headers=headers)
    assert response.status_code == 200 # Now they can list roles
