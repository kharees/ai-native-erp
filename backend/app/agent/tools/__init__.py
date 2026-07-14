"""
app/agent/tools/
==================
Tool registries for the AI OS layer, one module per business domain
(billing_tools.py is the first). Each module exposes a list of
ToolDefinition entries — name, description, JSON-schema input_schema,
required_permission, and a handler function — for a future orchestrator
to register with an LLM's tool-calling API and dispatch through.

No orchestrator exists yet. These definitions are the registry half of
that work; dispatch, RBAC enforcement against required_permission, and
conversation-level idempotency-key generation are all orchestrator
responsibilities not built here — see docs/ai-foundation.md and
docs/production-hardening.md for what's tracked as still missing.

CRITICAL — tenant_id and user_id are never part of any input_schema
------------------------------------------------------------------
No tool in this package accepts tenant_id or user_id as an LLM-provided
argument. They are real parameters on every handler function, but they
must always be supplied by the calling code from the authenticated
request/session context (the same tenant_id/user_id an HTTP endpoint
would get from TenantIDDep / request.state), never from model output.
An LLM choosing which tenant or user a tool call acts as would be a
direct cross-tenant authorization bypass — the exact class of bug
Sprint 5 #3/#4 spent real effort closing in the regular API. Adding a
tool here that lets a model supply either of these fields is a
regression of that work, not a new feature.
"""

from app.agent.tools.billing_tools import BILLING_TOOLS, ToolDefinition

__all__ = ["BILLING_TOOLS", "ToolDefinition"]
