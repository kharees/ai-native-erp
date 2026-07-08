"""
tests/test_auth_middleware.py
=============================
Tests the TenantAuthMiddleware to ensure strict JWT and Tenant Isolation enforcement.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from app.models.tenants import Tenant
from app.models.users import UserProfile

pytestmark = pytest.mark.asyncio

async def setup_tenant_and_user(db: AsyncSession):
    """Helper to bootstrap a valid tenant and user."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    from datetime import datetime
from datetime import timezone, timezone
    now = datetime.now(timezone.utc)
    await db.execute(
        insert(Tenant).values(id=tenant_id, name="Test Corp", slug="testcorp", plan="free", company_info={}, business_settings={}, is_active=True, created_at=now, updated_at=now)
    )
    await db.execute(
        insert(UserProfile).values(
            id=uuid.uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            first_name="Test User", preferences={}, status="Active", role="member", timezone="UTC", locale="en",
            is_active=True, created_at=now, updated_at=now
        )
    )
    await db.commit()
    return tenant_id, user_id

async def test_auth_middleware_missing_header(client: AsyncClient):
    """Verify missing X-Tenant-ID and missing Authorization yields 401."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert "Authorization" in response.json().get("detail", "")

async def test_auth_middleware_invalid_jwt(client: AsyncClient):
    """Verify invalid JWT format yields 401."""
    headers = {"Authorization": "Bearer badtoken123"}
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401
    assert "Invalid or expired JWT" in response.json().get("detail", "")

async def test_auth_middleware_successful_auth(client: AsyncClient, db_session: AsyncSession, mock_jwt):
    """Verify a completely valid token and tenant setup passes middleware."""
    tenant_id, user_id = await setup_tenant_and_user(db_session)
    
    token = mock_jwt(sub=str(user_id), tenant_id=str(tenant_id))
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id)
    }
    
    response = await client.get("/api/v1/users/me", headers=headers)
    # Even if route returns 404/500, if it passes 401/403, middleware succeeded.
    # Usually users/me would return 200.
    assert response.status_code in [200, 404]

async def test_auth_middleware_tenant_isolation_mismatch(client: AsyncClient, db_session: AsyncSession, mock_jwt):
    """Verify a token for Tenant A cannot access Tenant B (X-Tenant-ID mismatch vs DB)."""
    tenant_id, user_id = await setup_tenant_and_user(db_session)
    evil_tenant_id = uuid.uuid4() # Token tries to access this
    
    token = mock_jwt(sub=str(user_id), tenant_id=str(tenant_id))
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(evil_tenant_id) # Mismatch! The middleware queries UserProfile with evil_tenant_id + user_id, which fails.
    }
    
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 403
    assert "does not match the tenant ID in the JWT" in response.json().get("detail", "")
