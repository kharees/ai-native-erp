"""
app/agent/orchestrator/loop.py
================================
The Billing tool-calling loop. Two public entry points:

  run_turn(...)                -> drives the model through
                                   complete_with_tools() (app/services/ai/base.py),
                                   dispatching non-gated tool calls and
                                   pausing on the first requires_confirmation
                                   call in any batch.
  resume_after_confirmation(...) -> dispatches (or records the decline of)
                                   an EXACT previously-proposed tool call --
                                   never re-asks the model to decide again --
                                   then continues the loop via run_turn.

Design decisions, confirmed before this was written
-----------------------------------------------------
* Stateless per invocation: the caller owns conversation history (a
  list[AIMessage]) and persists whatever this returns. No conversation
  table here -- documented gap, not a silent one (see docs/ai-foundation.md).
* Confirmation is a hard pause, not a soft warning: encountering a
  requires_confirmation tool call stops the loop immediately and returns
  it verbatim to the caller. Nothing about it is executed until an
  explicit, byte-for-byte-unedited resume_after_confirmation call. If a
  human wants to change an argument first, that invalidates the captured
  tool_call_id -- the caller must let the model produce a fresh proposal
  instead of "confirming with edits", or idempotency silently breaks
  (see docs/production-hardening.md).
* If a tool-call batch contains a requires_confirmation call, NOTHING in
  that batch is dispatched yet -- not even earlier, non-gated calls in
  the same batch. Every other call in the batch gets a "deferred, not
  executed" tool_result (both providers require every tool_use/tool_call
  in an assistant turn to get a matching result before the next model
  call) so the model can re-request them next turn if still needed.
* idempotency_key = f"{conversation_id}:{tool_call_id}" for any handler
  that accepts one (detected via inspect.signature, not a hardcoded
  tool-name list -- so this doesn't silently stop working if a future
  tool's parameter set changes). The provider's own tool_call_id is
  already a stable per-decision identifier: a genuine retry of the same
  decision reuses it naturally, a new decision by the model gets a new one.
* STUCK_CONFLICT (409 from claim_idempotency_key, see docs/production-hardening.md,
  "Orchestrator retry logic MUST account for...") is terminal for that
  tool *for the rest of this invocation*: once hit, that tool name is
  added to a per-call stuck-set and any further request to call it in
  this same run_turn loop is refused locally (a firm, repeated
  tool_result) rather than dispatched again -- this is enforced in code,
  not left to the model reliably following an instruction not to retry.
* RBAC is enforced here, per dispatch, via app.middleware.rbac.check_permission
  -- the same function (not a reimplementation) the HTTP RequirePermission
  dependency uses, given tenant_id/user_id directly instead of pulled from
  a Request.
"""

from __future__ import annotations

import inspect
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.analytics_tools import ANALYTICS_TOOLS
from app.agent.tools.base import ToolDefinition
from app.agent.tools.billing_tools import BILLING_TOOLS
from app.agent.tools.finance_tools import FINANCE_TOOLS
from app.agent.tools.inventory_tools import INVENTORY_TOOLS
from app.agent.tools.migration_tools import MIGRATION_TOOLS
from app.agent.tools.security_tools import SECURITY_TOOLS
from app.core.database import db_session
from app.middleware.rbac import check_permission
from app.services.ai.base import AIMessage, AIProvider, AIToolCall
from app.services.ai.factory import get_ai_provider

# Every registered tool module -- get_tools_for_user (below) is the single
# place that knows the full set; no other module should need its own
# "all tools" list.
_ALL_TOOL_MODULES: list[list[ToolDefinition]] = [
    BILLING_TOOLS, FINANCE_TOOLS, INVENTORY_TOOLS, MIGRATION_TOOLS, SECURITY_TOOLS, ANALYTICS_TOOLS,
]

log = structlog.get_logger(__name__)

DEFAULT_MAX_ITERATIONS = 5

# Broadened from a Billing-only prompt to this general-purpose one as part
# of the 5-copilot consolidation: get_tools_for_user (the default tool
# source whenever a caller doesn't pass an explicit `tools=`) now spans
# billing, finance, inventory, migration, and security tools, not just
# Billing -- the default system prompt needs to match that breadth rather
# than telling the model it's "a billing assistant" while handing it a
# get_org_risk_score tool. No test depended on the old wording (checked
# before changing it).
DEFAULT_SYSTEM_PROMPT = (
    "You are an operations assistant for a multi-tenant ERP, with tools "
    "spanning billing, finance, inventory, migration, and security/identity. "
    "Use the available tools to look up real data and, where the tools "
    "support it, take actions on the user's behalf. Never invent amounts, "
    "IDs, dates, or any other figure -- look it up with a search/read tool "
    "or ask the user if you don't have it. Money-mutating or stock-mutating "
    "actions (e.g. create_invoice, record_payment, execute_stock_movement) "
    "require the user's explicit confirmation before they execute -- this is "
    "enforced by the system, not just this instruction. create_invoice can "
    "only create non-tax / zero-tax invoices; say so plainly if the user "
    "asks for tax handling this system doesn't support."
)

# Compose into a caller's system prompt when app.agent.tools.analytics_tools'
# ANALYTICS_TOOLS are included in a run_turn/resume_after_confirmation call
# -- e.g. system=DEFAULT_SYSTEM_PROMPT + " " + ANALYTICS_SYSTEM_PROMPT_ADDITION.
# Not folded into DEFAULT_SYSTEM_PROMPT itself: callers that don't include
# ANALYTICS_TOOLS shouldn't have this instruction appended for tools they
# can't even call. (app/api/v1/endpoints/agent_chat.py, the unified chat
# endpoint, always includes it -- get_tools_for_user always considers
# ANALYTICS_TOOLS in its merge.)
ANALYTICS_SYSTEM_PROMPT_ADDITION = (
    "You also have read-only analytics tools (sales summaries, top items, "
    "low stock, outstanding dues, customer summaries). Every figure they "
    "return comes from a real database query -- state only what a tool "
    "actually returned. Never estimate, extrapolate, round significantly, "
    "or fill in a number a tool didn't provide, even if asked to guess or "
    "approximate. If a question needs a figure no available tool provides, "
    "say so explicitly instead of approximating one."
)

_DEFERRED_DETAIL = (
    "Not executed -- another action requested in the same turn required "
    "human confirmation first. Re-request this action again if it's still "
    "needed."
)

_STUCK_DETAIL = (
    "This action may already be in progress, or a previous attempt failed "
    "in a way that cannot be automatically retried. Do NOT retry this exact "
    "action again in this conversation. Tell the user to check the current "
    "state manually (e.g. look up the invoice or payment by its reference "
    "number) before attempting it again."
)


class ToolOutcome(str, Enum):
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    STUCK_CONFLICT = "stuck_conflict"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN_TOOL = "unknown_tool"
    UNEXPECTED_ERROR = "unexpected_error"


@dataclass
class OrchestratorResult:
    """
    status:
      "done"                   -- text is the model's final answer.
      "awaiting_confirmation"  -- pending_tool_call is the exact proposed
                                   call; nothing has been dispatched. Pass
                                   it back unedited to resume_after_confirmation.
      "max_iterations_reached" -- safety cap hit without a final answer;
                                   text is None, messages has everything so
                                   far for the caller to inspect/persist.
    messages: the full updated history -- always safe to pass back into
      the next run_turn/resume_after_confirmation call as-is.
    """
    status: str
    text: str | None = None
    pending_tool_call: AIToolCall | None = None
    messages: list[AIMessage] = field(default_factory=list)


def _tool_result_message(tool_call_id: str, payload: dict[str, Any]) -> AIMessage:
    return {"role": "tool_result", "tool_call_id": tool_call_id, "content": json.dumps(payload, default=str)}


async def _check_tool_permission(tool: ToolDefinition, tenant_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    async with db_session() as db:
        return await check_permission(db, tenant_id, user_id, *tool.required_permission)


async def get_tools_for_user(tenant_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> list[ToolDefinition]:
    """
    Merges every registered tool module (billing, finance, inventory,
    migration, security, analytics -- see _ALL_TOOL_MODULES) and filters
    to only the tools this user's RBAC permissions actually allow, BEFORE
    the tool list is ever sent to the model.

    This is defense-in-depth / UX, not the only enforcement boundary: a
    tool this filters out can never even be proposed, but _dispatch's own
    check_permission call (via _check_tool_permission) remains the real
    enforcement point regardless -- a tool call is never dispatched on
    trust that the model only saw permitted tools; the same check runs
    again right before every dispatch.
    """
    all_tools = [tool for module in _ALL_TOOL_MODULES for tool in module]
    allowed: list[ToolDefinition] = []
    for tool in all_tools:
        if await check_permission(db, tenant_id, user_id, *tool.required_permission):
            allowed.append(tool)
    return allowed


async def _dispatch(
    tool: ToolDefinition,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: str,
    call: AIToolCall,
) -> tuple[ToolOutcome, dict[str, Any]]:
    if not await _check_tool_permission(tool, tenant_id, user_id):
        log.warning("agent_tool.permission_denied", tool=tool.name, tenant_id=str(tenant_id), user_id=str(user_id))
        return ToolOutcome.PERMISSION_DENIED, {
            "error": True, "type": "permission_denied",
            "detail": f"Missing required permission for '{tool.name}'.",
        }

    # Model-supplied arguments only ever include what's in the tool's
    # input_schema (never tenant_id/user_id/idempotency_key -- see the
    # package docstring's hard rule). Inject whichever of those this
    # specific handler actually accepts, detected from its real signature
    # rather than a hardcoded per-tool-name list, so this doesn't silently
    # stop injecting idempotency_key if a handler's parameters change.
    kwargs: dict[str, Any] = dict(call["arguments"])
    handler_params = inspect.signature(tool.handler).parameters
    if "tenant_id" in handler_params:
        kwargs["tenant_id"] = tenant_id
    if "user_id" in handler_params:
        kwargs["user_id"] = user_id
    if "idempotency_key" in handler_params:
        kwargs["idempotency_key"] = f"{conversation_id}:{call['id']}"

    try:
        response = await tool.handler(**kwargs)
        log.info("agent_tool.dispatched", tool=tool.name, tenant_id=str(tenant_id), outcome="success")
        return ToolOutcome.SUCCESS, response
    except HTTPException as exc:
        if exc.status_code == 409:
            log.warning("agent_tool.stuck_conflict", tool=tool.name, tenant_id=str(tenant_id), detail=exc.detail)
            return ToolOutcome.STUCK_CONFLICT, {"error": True, "type": "stuck_conflict", "detail": _STUCK_DETAIL}
        log.info("agent_tool.validation_error", tool=tool.name, status_code=exc.status_code, detail=exc.detail)
        return ToolOutcome.VALIDATION_ERROR, {"error": True, "type": "validation_error", "detail": exc.detail}
    except Exception as exc:
        log.error("agent_tool.unexpected_error", tool=tool.name, error=str(exc), exc_info=True)
        return ToolOutcome.UNEXPECTED_ERROR, {
            "error": True, "type": "unexpected_error",
            "detail": "An unexpected error occurred while executing this action.",
        }


async def run_turn(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: str,
    messages: list[AIMessage],
    provider: AIProvider | None = None,
    tools: list[ToolDefinition] | None = None,
    system: str | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    _stuck_call_ids: set[str] | None = None,
) -> OrchestratorResult:
    """
    messages must already include the new user turn -- this function does
    not append one; the caller builds the conversation, this function only
    drives the tool-calling loop over it. tenant_id/user_id/conversation_id
    come from the caller's authenticated context, never from model output.
    """
    provider = provider or get_ai_provider()
    if tools is not None:
        tool_list = tools
    else:
        async with db_session() as db:
            tool_list = await get_tools_for_user(tenant_id, user_id, db)
    tools_by_name = {t.name: t for t in tool_list}
    provider_tools = [t.to_provider_schema() for t in tool_list]

    messages = list(messages)  # never mutate the caller's list in place
    # Tracked by tool_call_id, not tool name -- a stuck create_invoice call
    # must not block every *other* future invoice in the same conversation,
    # only a repeat of that exact same call_id (e.g. a model response
    # containing the same tool_use twice, or a stuck call surfacing again
    # via a later batch that still references the same original id).
    stuck_call_ids = set(_stuck_call_ids) if _stuck_call_ids else set()

    for _ in range(max_iterations):
        result = await provider.complete_with_tools(
            messages, provider_tools, system=system or DEFAULT_SYSTEM_PROMPT
        )

        if not result.tool_calls:
            return OrchestratorResult(status="done", text=result.text, messages=messages)

        # Replay the assistant's own turn verbatim before anything else --
        # both providers require their prior tool-call turn present in
        # history for the tool-result turns that follow it to make sense.
        messages.append({"role": "assistant", "content": result.text, "tool_calls": result.tool_calls})

        confirmation_needed = next(
            (call for call in result.tool_calls
             if getattr(tools_by_name.get(call["name"]), "requires_confirmation", False)),
            None,
        )
        if confirmation_needed is not None:
            # Nothing in this batch dispatches yet -- every other call gets
            # a "deferred" result so the protocol contract (every tool_use
            # gets a tool_result) still holds; the gated call gets none,
            # pending resume_after_confirmation.
            for call in result.tool_calls:
                if call["id"] != confirmation_needed["id"]:
                    messages.append(_tool_result_message(
                        call["id"], {"error": True, "type": "deferred", "detail": _DEFERRED_DETAIL}
                    ))
            return OrchestratorResult(status="awaiting_confirmation", pending_tool_call=confirmation_needed, messages=messages)

        for call in result.tool_calls:
            tool = tools_by_name.get(call["name"])

            if tool is None:
                log.warning("agent_tool.unknown_tool", tool_name=call["name"])
                messages.append(_tool_result_message(
                    call["id"], {"error": True, "type": "unknown_tool", "detail": f"No such tool: '{call['name']}'."}
                ))
                continue

            if call["id"] in stuck_call_ids:
                messages.append(_tool_result_message(
                    call["id"], {"error": True, "type": "stuck_conflict", "detail": _STUCK_DETAIL}
                ))
                continue

            outcome, payload = await _dispatch(tool, tenant_id, user_id, conversation_id, call)
            if outcome == ToolOutcome.STUCK_CONFLICT:
                stuck_call_ids.add(call["id"])
            messages.append(_tool_result_message(call["id"], payload))

    return OrchestratorResult(status="max_iterations_reached", messages=messages)


async def resume_after_confirmation(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: str,
    messages: list[AIMessage],
    pending_tool_call: AIToolCall,
    confirmed: bool,
    provider: AIProvider | None = None,
    tools: list[ToolDefinition] | None = None,
    system: str | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> OrchestratorResult:
    """
    pending_tool_call must be exactly what a prior run_turn/
    resume_after_confirmation call returned as OrchestratorResult.pending_tool_call
    -- same id, same arguments, unedited. Dispatching (when confirmed=True)
    uses that captured id/arguments directly; the model is never re-asked
    to decide this action again. If a human wants to change an argument,
    that is a new decision -- the caller should let the model produce a
    fresh proposal (a new run_turn) instead of calling this with edited
    arguments, or idempotency_key = f"{conversation_id}:{tool_call_id}"
    silently reuses the old key for what is actually a different action.
    """
    if tools is not None:
        tool_list = tools
    else:
        async with db_session() as db:
            tool_list = await get_tools_for_user(tenant_id, user_id, db)
    tools_by_name = {t.name: t for t in tool_list}
    tool = tools_by_name.get(pending_tool_call["name"])

    messages = list(messages)

    if tool is None:
        log.warning("agent_tool.unknown_tool_on_resume", tool_name=pending_tool_call["name"])
        payload = {"error": True, "type": "unknown_tool", "detail": f"No such tool: '{pending_tool_call['name']}'."}
    elif not confirmed:
        log.info("agent_tool.confirmation_declined", tool=tool.name, tenant_id=str(tenant_id))
        payload = {"error": False, "type": "declined", "detail": "The user declined to proceed with this action."}
    else:
        outcome, payload = await _dispatch(tool, tenant_id, user_id, conversation_id, pending_tool_call)
        stuck = {pending_tool_call["id"]} if outcome == ToolOutcome.STUCK_CONFLICT else set()
        messages.append(_tool_result_message(pending_tool_call["id"], payload))
        return await run_turn(
            tenant_id=tenant_id, user_id=user_id, conversation_id=conversation_id,
            messages=messages, provider=provider, tools=tool_list, system=system,
            max_iterations=max_iterations, _stuck_call_ids=stuck,
        )

    messages.append(_tool_result_message(pending_tool_call["id"], payload))
    return await run_turn(
        tenant_id=tenant_id, user_id=user_id, conversation_id=conversation_id,
        messages=messages, provider=provider, tools=tool_list, system=system,
        max_iterations=max_iterations,
    )
