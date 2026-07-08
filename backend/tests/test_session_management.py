"""
tests/test_session_management.py
================================
Validates Session & Device tracking, Force Logout, and Middleware verification.
"""

import uuid
from datetime import datetime
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from app.models.tenants import Tenant
from app.models.users import UserProfile
from app.models.sessions import TenantSession

pytestmark = pytest.mark.asyncio

async def setup_session(db: AsyncSession):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    
    from datetime import datetime
    now = datetime.now(timezone.utc)
    
    await db.execute(insert(Tenant).values(id=tenant_id, name="Sess Corp", slug="sess", plan="free", company_info={}, business_settings={}, is_active=True, created_at=now, updated_at=now))
    up_id = uuid.uuid4()
    await db.execute(
        insert(UserProfile).values(
            id=up_id, user_id=user_id, tenant_id=tenant_id, first_name="Test User", preferences={}, status="Active", role="member", timezone="UTC", locale="en", is_active=True, created_at=now, updated_at=now
        )
    )
    
    await db.execute(
        insert(TenantSession).values(
            id=session_id,
            tenant_id=tenant_id,
            user_id=up_id,
            is_active=True,
            expires_at=now + timedelta(days=1),
            last_active_at=now,
            created_at=now
        )
    )
    await db.commit()
    return tenant_id, user_id, session_id

async def test_active_session_auth(client: AsyncClient, db_session: AsyncSession, mock_jwt):
    """An active session should pass auth middleware."""
    tenant_id, user_id, session_id = await setup_session(db_session)
    token = mock_jwt(sub=str(user_id), tenant_id=str(tenant_id), session_id=str(session_id))
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}
    
    response = await client.get("/api/v1/sessions/me", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

async def test_revoked_session_blocked(client: AsyncClient, db_session: AsyncSession, mock_jwt):
    """A revoked session (is_active=False) should trigger a 401 Force Logout."""
    tenant_id, user_id, session_id = await setup_session(db_session)
    
    session_obj = await db_session.get(TenantSession, session_id)
    session_obj.is_active = False
    await db_session.commit()
    
    token = mock_jwt(sub=str(user_id), tenant_id=str(tenant_id), session_id=str(session_id))
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}
    
    response = await client.get("/api/v1/sessions/me", headers=headers)
    assert response.status_code == 401

async def test_revoke_all_sessions_endpoint(client: AsyncClient, db_session: AsyncSession, mock_jwt):
    """Hitting DELETE /sessions/me/all should revoke sessions."""
    tenant_id, user_id, session_id = await setup_session(db_session)
    token = mock_jwt(sub=str(user_id), tenant_id=str(tenant_id), session_id=str(session_id))
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}
    
    res = await client.delete("/api/v1/sessions/me/all", headers=headers)
    assert res.status_code == 204
    
    from sqlalchemy import select
    from app.models.sessions import TenantSession
    result = await db_session.execute(select(TenantSession.is_active).where(TenantSession.id == session_id))
    is_active = result.scalar()
    assert is_active is False
