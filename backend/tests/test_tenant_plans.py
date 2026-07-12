"""
tests/test_tenant_plans.py
=============================
Validates tenant plan seat-limit enforcement (Sprint 4 #35):
tenants.plan was read and logged by TenantAuthMiddleware but never
actually checked against anything. POST /users/ (user provisioning) now
enforces PLAN_LIMITS.max_users.
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.auth import UserAccount
from app.models.tenants import Tenant
from app.models.users import UserProfile

pytestmark = pytest.mark.asyncio


async def _make_tenant_with_users(db: AsyncSession, plan: str, existing_users: int) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db.execute(insert(Tenant).values(
        id=tenant_id, name=f"Plan Test {plan}", slug=f"plan-{tenant_id.hex[:8]}",
        plan=plan, company_info={}, business_settings={}, is_active=True,
        created_at=now, updated_at=now,
    ))
    for _ in range(existing_users):
        user_id = uuid.uuid4()
        await db.execute(insert(UserAccount).values(
            id=user_id, email=f"{user_id}@test.local", hashed_password=get_password_hash("x"),
            is_active=True, created_at=now, updated_at=now,
        ))
        await db.execute(insert(UserProfile).values(
            id=uuid.uuid4(), user_id=user_id, tenant_id=tenant_id, first_name="Seat",
            preferences={}, status="Active", role="member", timezone="UTC", locale="en",
            is_active=True, created_at=now, updated_at=now,
        ))
    await db.commit()
    return tenant_id


async def _make_caller(db: AsyncSession, tenant_id: uuid.UUID, mock_jwt) -> dict:
    """Creates the acting admin user (distinct from the seat-consuming
    users _make_tenant_with_users pre-fills) — TenantAuthMiddleware's
    validation query requires a real UserProfile row matching the JWT's
    `sub` claim for the given tenant, or it 403s as "tenant not found"
    before the request ever reaches the route handler."""
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db.execute(insert(UserAccount).values(
        id=user_id, email=f"{user_id}@test.local", hashed_password=get_password_hash("x"),
        is_active=True, created_at=now, updated_at=now,
    ))
    await db.execute(insert(UserProfile).values(
        id=uuid.uuid4(), user_id=user_id, tenant_id=tenant_id, first_name="Caller",
        preferences={}, status="Active", role="admin", timezone="UTC", locale="en",
        is_active=True, created_at=now, updated_at=now,
    ))
    await db.commit()
    token = mock_jwt(sub=str(user_id), tenant_id=str(tenant_id))
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}


async def test_free_plan_blocks_provisioning_past_seat_limit(async_client: AsyncClient, db_session: AsyncSession, mock_jwt):
    # PLAN_LIMITS["free"].max_users == 5 — pre-fill exactly 5 seats.
    tenant_id = await _make_tenant_with_users(db_session, "free", existing_users=5)
    headers = await _make_caller(db_session, tenant_id, mock_jwt)

    resp = await async_client.post(
        "/api/v1/users/",
        headers=headers,
        json={"email": f"{uuid.uuid4()}@example.com", "password": "SomePass123!", "first_name": "Overflow", "roles": []},
    )
    assert resp.status_code == 402
    assert "plan" in resp.json()["detail"].lower()


async def test_enterprise_plan_has_no_seat_limit(async_client: AsyncClient, db_session: AsyncSession, mock_jwt):
    tenant_id = await _make_tenant_with_users(db_session, "enterprise", existing_users=5)
    headers = await _make_caller(db_session, tenant_id, mock_jwt)

    resp = await async_client.post(
        "/api/v1/users/",
        headers=headers,
        json={"email": f"{uuid.uuid4()}@example.com", "password": "SomePass123!", "first_name": "SixthSeat", "roles": []},
    )
    assert resp.status_code == 201


async def test_free_plan_allows_provisioning_under_seat_limit(async_client: AsyncClient, db_session: AsyncSession, mock_jwt):
    tenant_id = await _make_tenant_with_users(db_session, "free", existing_users=2)
    headers = await _make_caller(db_session, tenant_id, mock_jwt)

    resp = await async_client.post(
        "/api/v1/users/",
        headers=headers,
        json={"email": f"{uuid.uuid4()}@example.com", "password": "SomePass123!", "first_name": "ThirdSeat", "roles": []},
    )
    assert resp.status_code == 201
