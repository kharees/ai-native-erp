"""
tests/test_audit_logging.py
===========================
Validates the AuditLogger service and APIs.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from app.models.tenants import Tenant
from app.models.users import UserProfile
from app.services.audit import AuditLogger
from fastapi import Request

pytestmark = pytest.mark.asyncio

async def setup_audit_scenario(db: AsyncSession):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    from datetime import datetime
    now = datetime.now(timezone.utc)
    
    await db.execute(insert(Tenant).values(id=tenant_id, name="Audit Corp", slug="audit", plan="free", company_info={}, business_settings={}, is_active=True, created_at=now, updated_at=now))
    up_id = uuid.uuid4()
    await db.execute(
        insert(UserProfile).values(
            id=up_id, user_id=user_id, tenant_id=tenant_id, first_name="Test User", preferences={}, status="Active", role="member", timezone="UTC", locale="en", is_active=True, created_at=now, updated_at=now
        )
    )
    await db.commit()
    return tenant_id, user_id

async def test_audit_logger_service(db_session: AsyncSession):
    """Verify that logging an action directly inserts a record."""
    tenant_id, user_id = await setup_audit_scenario(db_session)
    
    # We must mock a starlette request because AuditLogger extracts client IP
    # Since we are calling the service directly, we'll mock request.state.
    from types import SimpleNamespace
    mock_req = SimpleNamespace(
        state=SimpleNamespace(tenant_id=tenant_id, user_id=user_id, request_id="req-123"),
        client=SimpleNamespace(host="192.168.1.1"),
        headers={"user-agent": "pytest"}
    )
    
    # Cast to Request to bypass type checker if needed, but python allows duck typing
    await AuditLogger.log_action(
        db=db_session,
        request=mock_req, # type: ignore
        action_category="AUTH",
        action_type="LOGIN_SUCCESS",
        resource_id=str(user_id)
    )
    
    from sqlalchemy import select, func
    from app.models.audit import TenantAuditLog
    result = await db_session.execute(select(func.count()).select_from(TenantAuditLog).where(TenantAuditLog.tenant_id == tenant_id))
    count = result.scalar()
    assert count == 1
