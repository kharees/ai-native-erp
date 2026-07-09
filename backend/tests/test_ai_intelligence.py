"""
tests/test_ai_intelligence.py
=============================
Validates AI Intelligence heuristics (Account Risk Score, Inactive Users, etc).
"""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from app.models.tenants import Tenant
from app.models.users import UserProfile
from app.models.auth import UserAccount
from app.models.audit import TenantAuditLog
from app.services.ai_intelligence import SecurityAnalyzer, IdentityAnalyzer

pytestmark = pytest.mark.asyncio

async def setup_ai_scenario(db: AsyncSession):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    await db.execute(insert(Tenant).values(id=tenant_id, name="AI Corp", slug="ai", plan="free", company_info={}, business_settings={}, is_active=True, created_at=now, updated_at=now))
    await db.execute(
        insert(UserAccount).values(
            id=user_id, email=f"{user_id}@test.local", hashed_password="not-a-real-hash", is_active=True, created_at=now, updated_at=now
        )
    )
    up_id = uuid.uuid4()
    await db.execute(
        insert(UserProfile).values(
            id=up_id, user_id=user_id, tenant_id=tenant_id, first_name="Test User", preferences={}, status="Active", role="member", timezone="UTC", locale="en", is_active=True, created_at=now, updated_at=now
        )
    )
    await db.commit()
    return tenant_id, user_id, up_id

async def test_security_score_brute_force(db_session: AsyncSession):
    """Verify that 60 failed logins degrade the risk score heavily."""
    tenant_id, user_id, up_id = await setup_ai_scenario(db_session)
    
    # Inject 60 failed logins
    now = datetime.now(timezone.utc)
    logs = []
    for i in range(60):
        logs.append({
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action_category": "AUTH",
            "action_type": "LOGIN_FAILED",
            "action_source": "API",
            "created_at": now
        })
    await db_session.execute(insert(TenantAuditLog).values(logs))
    await db_session.commit()
    
    result = await SecurityAnalyzer.calculate_org_risk_score(db_session, tenant_id)
    assert result["score"] <= 80
    assert any("High brute force activity" in inc for inc in result["active_incidents"])

async def test_inactive_users_detection(db_session: AsyncSession):
    """Verify users with no sessions are flagged."""
    tenant_id, user_id, up_id = await setup_ai_scenario(db_session)
    # The setup created a user but no session. They should appear inactive.
    
    inactive = await IdentityAnalyzer.get_inactive_users(db_session, tenant_id, days_inactive=30)
    assert len(inactive) == 1
    assert inactive[0]["name"] == "Test User"
