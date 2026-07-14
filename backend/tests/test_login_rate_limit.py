"""
tests/test_login_rate_limit.py
================================
Verifies /auth/login's brute-force rate limit (5 attempts / 15 minutes /
IP, see app/api/v1/endpoints/auth.py + app/core/rate_limit.py).

limiter.reset() brackets the test: slowapi's Limiter is a module-level
singleton with in-memory storage shared across the whole pytest session,
and httpx's ASGITransport gives every test request the same client host —
so every test hitting /login shares one counter. Resetting before and
after keeps this test isolated from (and non-polluting toward) any other
test file that also calls /login (e.g. test_auth_cookie_flow.py).
"""
import pytest
from httpx import AsyncClient

from app.core.rate_limit import limiter

pytestmark = pytest.mark.asyncio


async def test_sixth_login_attempt_within_window_returns_429(async_client: AsyncClient):
    limiter.reset()
    try:
        payload = {"email": "rate-limit-test@example.com", "password": "wrong-password"}
        responses = [await async_client.post("/api/v1/auth/login", json=payload) for _ in range(6)]

        for resp in responses[:5]:
            assert resp.status_code == 401, resp.text

        assert responses[5].status_code == 429, responses[5].text
        assert "detail" in responses[5].json()
    finally:
        limiter.reset()
