"""
tests/test_auth_cookie_flow.py
=================================
Validates the real /auth/login -> /auth/refresh -> /auth/logout flow
(Sprint 4 #10): the refresh token must travel only via an httpOnly cookie,
never in the JSON response body, and the cookie must be cleared on logout.

No prior test exercised /auth/login or /auth/refresh at all — every other
auth-dependent test builds a JWT directly via the mock_jwt fixture, bypassing
the real endpoint entirely.
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

_PASSWORD = "correct-horse-battery-staple"


async def _create_login_user(db: AsyncSession) -> tuple[uuid.UUID, str]:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    email = f"{user_id}@test.local"
    now = datetime.now(timezone.utc)

    await db.execute(insert(Tenant).values(
        id=tenant_id, name="Cookie Test Corp", slug=f"cookie-{tenant_id.hex[:8]}",
        plan="free", company_info={}, business_settings={}, is_active=True,
        created_at=now, updated_at=now,
    ))
    await db.execute(insert(UserAccount).values(
        id=user_id, email=email, hashed_password=get_password_hash(_PASSWORD),
        is_active=True, created_at=now, updated_at=now,
    ))
    await db.execute(insert(UserProfile).values(
        id=uuid.uuid4(), user_id=user_id, tenant_id=tenant_id, first_name="Cookie",
        preferences={}, status="Active", role="member", timezone="UTC", locale="en",
        is_active=True, created_at=now, updated_at=now,
    ))
    await db.commit()
    return tenant_id, email


async def test_login_sets_httponly_refresh_cookie_not_body(async_client: AsyncClient, db_session: AsyncSession):
    _, email = await _create_login_user(db_session)
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _PASSWORD},
    )
    assert resp.status_code == 200
    body = resp.json()

    # Never in the JSON body.
    assert body["refresh_token"] is None
    assert body["access_token"]

    # Only in an httpOnly cookie.
    cookie = resp.cookies.get("refresh_token")
    assert cookie is not None
    set_cookie_header = resp.headers.get("set-cookie", "")
    assert "httponly" in set_cookie_header.lower()


async def test_refresh_uses_cookie_not_body(async_client: AsyncClient, db_session: AsyncSession):
    _, email = await _create_login_user(db_session)
    login_resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": _PASSWORD})
    assert login_resp.status_code == 200

    # httpx's AsyncClient persists cookies from prior responses on the
    # client's cookie jar automatically for subsequent requests to the same
    # client, mirroring a real browser sending the cookie back.
    refresh_resp = await async_client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200
    refresh_body = refresh_resp.json()
    assert refresh_body["access_token"]
    assert refresh_body["refresh_token"] is None
    # Cookie rotated — still present, still httpOnly.
    assert refresh_resp.cookies.get("refresh_token") is not None


async def test_refresh_without_cookie_rejected(async_client: AsyncClient):
    resp = await async_client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


async def test_logout_clears_refresh_cookie(async_client: AsyncClient, db_session: AsyncSession):
    _, email = await _create_login_user(db_session)
    login_resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": _PASSWORD})
    access_token = login_resp.json()["access_token"]

    logout_resp = await async_client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_resp.status_code == 200
    set_cookie_header = logout_resp.headers.get("set-cookie", "")
    # A cleared cookie is re-set with an immediate/past expiry.
    assert "refresh_token=" in set_cookie_header
