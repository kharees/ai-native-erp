"""
tests/test_agent_chat_rate_limit.py
======================================
Verifies the per-user rate limits on the unified AI chat endpoint
(app/api/v1/endpoints/agent_chat.py): 20/minute on POST /agent/chat,
30/minute on POST /agent/chat/confirm, keyed on the authenticated user_id
(app.core.rate_limit.user_or_ip_key), not just IP.

run_turn/resume_after_confirmation are mocked at the point agent_chat.py
imports them -- this test is about the rate-limit wrapper around the
endpoint, not the orchestrator/LLM behavior underneath it (already
covered by tests/test_orchestrator.py).

limiter.reset() brackets each test -- see test_login_rate_limit.py's own
docstring for why (module-level singleton limiter, shared in-memory
storage, one client host per test run via httpx's ASGITransport).
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.rate_limit import limiter

pytestmark = pytest.mark.asyncio

_FAKE_RESULT = SimpleNamespace(status="done", text="ok", pending_tool_call=None, messages=[])


async def test_21st_chat_request_within_a_minute_returns_429(async_client: AsyncClient, auth_headers: dict):
    limiter.reset()
    try:
        with patch("app.api.v1.endpoints.agent_chat.run_turn", AsyncMock(return_value=_FAKE_RESULT)):
            payload = {
                "conversation_id": "rate-limit-test-chat",
                "messages": [{"role": "user", "content": "hello"}],
            }
            responses = [
                await async_client.post("/api/v1/agent/chat", json=payload, headers=auth_headers)
                for _ in range(21)
            ]

        for resp in responses[:20]:
            assert resp.status_code == 200, resp.text

        assert responses[20].status_code == 429, responses[20].text
        body = responses[20].json()
        assert body["detail"]["type"] == "rate_limit_exceeded"
    finally:
        limiter.reset()


async def test_31st_chat_confirm_request_within_a_minute_returns_429(async_client: AsyncClient, auth_headers: dict):
    limiter.reset()
    try:
        with patch("app.api.v1.endpoints.agent_chat.resume_after_confirmation", AsyncMock(return_value=_FAKE_RESULT)):
            payload = {
                "conversation_id": "rate-limit-test-confirm",
                "messages": [{"role": "user", "content": "hello"}],
                "pending_tool_call": {"id": "call_1", "name": "search_customer", "arguments": {}},
                "confirmed": True,
            }
            responses = [
                await async_client.post("/api/v1/agent/chat/confirm", json=payload, headers=auth_headers)
                for _ in range(31)
            ]

        for resp in responses[:30]:
            assert resp.status_code == 200, resp.text

        assert responses[30].status_code == 429, responses[30].text
    finally:
        limiter.reset()


async def test_chat_rate_limit_is_scoped_per_user_not_shared_globally(
    async_client: AsyncClient, auth_headers: dict, alt_tenant_headers: dict,
):
    """A different (real) user must have their own independent bucket --
    exhausting one user's limit must not affect another user's requests,
    proving the limit is keyed on user_id and not e.g. a single shared
    process-wide counter."""
    limiter.reset()
    try:
        with patch("app.api.v1.endpoints.agent_chat.run_turn", AsyncMock(return_value=_FAKE_RESULT)):
            payload = {"conversation_id": "scope-test", "messages": [{"role": "user", "content": "hi"}]}

            for _ in range(20):
                resp = await async_client.post("/api/v1/agent/chat", json=payload, headers=auth_headers)
                assert resp.status_code == 200, resp.text

            exhausted_resp = await async_client.post("/api/v1/agent/chat", json=payload, headers=auth_headers)
            assert exhausted_resp.status_code == 429, exhausted_resp.text

            # A different user (alt_tenant_headers) is unaffected.
            other_user_resp = await async_client.post("/api/v1/agent/chat", json=payload, headers=alt_tenant_headers)
            assert other_user_resp.status_code == 200, other_user_resp.text
    finally:
        limiter.reset()
