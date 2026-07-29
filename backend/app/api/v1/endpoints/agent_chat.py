"""
app/api/v1/endpoints/agent_chat.py
=====================================
The unified AI chat endpoint (5-copilot consolidation): any authenticated
user can call this regardless of which module they're currently viewing.
Available tools are resolved per-request by app.agent.orchestrator.loop's
get_tools_for_user(tenant_id, user_id, db) -- filtered by that user's real
RBAC permissions BEFORE the tool list is ever sent to the model, so a user
without finance permissions never even sees finance tools as an option
(let alone gets to dispatch one -- _dispatch's own check_permission call
remains the actual enforcement boundary regardless).

No RequirePermission dependency on these routes themselves -- gating who
can chat at all isn't the point; gating which tools a given chat can use
is, and that already happens per-tool inside get_tools_for_user/_dispatch.

Rate limiting: keyed on the authenticated user_id (falling back to IP for
an unauthenticated caller), not just IP -- see
app.core.rate_limit.user_or_ip_key. /chat is capped tighter than
/chat/confirm since each /chat turn can trigger a real LLM call (the
expensive, abusable resource), while /chat/confirm only replays a single
already-decided tool call.
"""

from fastapi import APIRouter, HTTPException, Request

from app.agent.orchestrator.loop import (
    ANALYTICS_SYSTEM_PROMPT_ADDITION,
    DEFAULT_SYSTEM_PROMPT,
    resume_after_confirmation,
    run_turn,
)
from app.core.rate_limit import limiter, user_or_ip_key
from app.middleware.tenant_auth import TenantIDDep, UserIDDep
from app.schemas.agent_chat import AgentChatConfirmRequest, AgentChatRequest, AgentChatResponse

router = APIRouter()


def _require_user_id(user_id: UserIDDep):
    if user_id is None:
        raise HTTPException(status_code=401, detail="A verified user is required to use the AI assistant.")
    return user_id


def _system_prompt(module_context: str | None) -> str:
    system = f"{DEFAULT_SYSTEM_PROMPT} {ANALYTICS_SYSTEM_PROMPT_ADDITION}"
    if module_context:
        system += (
            f" The user is currently viewing the '{module_context}' section of the app -- "
            f"prioritize tools relevant to it if the request is ambiguous, but you are not "
            f"restricted to only that module's tools."
        )
    return system


@router.post("/chat", response_model=AgentChatResponse)
@limiter.limit("20/minute", key_func=user_or_ip_key)
async def agent_chat(request: Request, payload: AgentChatRequest, tenant_id: TenantIDDep, user_id: UserIDDep):
    user_id = _require_user_id(user_id)

    result = await run_turn(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=payload.conversation_id,
        messages=[m.model_dump(exclude_none=True) for m in payload.messages],
        system=_system_prompt(payload.module_context),
    )
    return AgentChatResponse(
        status=result.status,
        text=result.text,
        pending_tool_call=result.pending_tool_call,
        messages=result.messages,
    )


@router.post("/chat/confirm", response_model=AgentChatResponse)
@limiter.limit("30/minute", key_func=user_or_ip_key)
async def agent_chat_confirm(request: Request, payload: AgentChatConfirmRequest, tenant_id: TenantIDDep, user_id: UserIDDep):
    user_id = _require_user_id(user_id)

    result = await resume_after_confirmation(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=payload.conversation_id,
        messages=[m.model_dump(exclude_none=True) for m in payload.messages],
        pending_tool_call=payload.pending_tool_call.model_dump(),
        confirmed=payload.confirmed,
    )
    return AgentChatResponse(
        status=result.status,
        text=result.text,
        pending_tool_call=result.pending_tool_call,
        messages=result.messages,
    )
