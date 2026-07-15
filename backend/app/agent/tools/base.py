"""
app/agent/tools/base.py
=========================
ToolDefinition — the shared registry-entry shape every module's tool
registry (billing_tools.py, and inventory/finance once those exist) uses.
Lives here rather than inside billing_tools.py specifically so a future
module imports the same class instead of redefining an identical
dataclass — one consistent shape for the orchestrator to dispatch
against, the same "one enforcement point, not several parallel ones"
principle already applied to @agent_tool (app/services/agent_adapters/base.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class ToolDefinition:
    """One registry entry: everything the orchestrator needs to describe
    this tool to an LLM, enforce authorization before calling it, and
    dispatch the call. required_permission is (module, feature, action) —
    the same three strings already passed to RequirePermission in the
    corresponding HTTP endpoint; the orchestrator is responsible for
    checking it (not enforced by the handler itself — handlers have no
    request/RBAC context to check against).

    requires_confirmation: True for anything that mutates real state in a
    way a human should approve before it happens (money-mutating tools,
    e.g. create_invoice/record_payment). The orchestrator loop pauses and
    returns the exact proposed tool call to the caller instead of
    dispatching it; only an explicit, unedited confirmation resumes and
    dispatches that same captured call. Defaults to False — most tools
    (e.g. a read-only search) don't need this gate."""
    name: str
    description: str
    input_schema: dict[str, Any]
    required_permission: tuple[str, str, str]
    handler: Callable[..., Awaitable[dict[str, Any]]]
    requires_confirmation: bool = False

    def to_provider_schema(self) -> dict[str, Any]:
        """Shape expected by AIProvider.complete_with_tools()'s `tools`
        parameter (app/services/ai/base.py) -- Anthropic's own native
        tools= shape, which every provider implementation translates from.
        Excludes required_permission and handler: those are orchestrator-
        internal, never sent to the model."""
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}
