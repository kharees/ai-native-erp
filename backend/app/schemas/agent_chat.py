"""
app/schemas/agent_chat.py
============================
Request/response shapes for the unified agent chat endpoint
(app/api/v1/endpoints/agent_chat.py), wrapping app.agent.orchestrator.loop's
run_turn()/resume_after_confirmation().

Stateless per the orchestrator's own design (see loop.py's docstring: "No
conversation table here -- documented gap, not a silent one"). The client
owns conversation history: `messages` in AgentChatRequest must include the
full prior history plus the new user turn, and every response returns the
updated `messages` for the client to store and resend next turn. This is a
deliberate consequence of an existing, already-confirmed design decision,
not something introduced here.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AgentToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class AgentMessage(BaseModel):
    """Mirrors app.services.ai.base.AIMessage exactly (see that module for
    the three turn shapes this represents) -- kept as a separate Pydantic
    schema rather than reusing the TypedDict directly, since FastAPI needs
    a real Pydantic model for request/response validation."""
    role: str
    content: str | list[dict[str, Any]] | None = None
    tool_calls: list[AgentToolCall] | None = None
    tool_call_id: str | None = None


class AgentChatRequest(BaseModel):
    conversation_id: str
    messages: list[AgentMessage]
    # Optional page-aware hint (e.g. "finance", "universal-inventory") --
    # appended to the system prompt so the model knows what the user is
    # looking at, but never restricts which tools it can call; a user on
    # the Finance page can still ask a billing or inventory question and
    # get real tools for it, filtered only by their RBAC permissions (see
    # get_tools_for_user), not by which page they happen to be on.
    module_context: str | None = None


class AgentChatResponse(BaseModel):
    status: str  # "done" | "awaiting_confirmation" | "max_iterations_reached"
    text: str | None = None
    pending_tool_call: AgentToolCall | None = None
    messages: list[AgentMessage]


class AgentChatConfirmRequest(BaseModel):
    conversation_id: str
    messages: list[AgentMessage]
    pending_tool_call: AgentToolCall
    confirmed: bool
