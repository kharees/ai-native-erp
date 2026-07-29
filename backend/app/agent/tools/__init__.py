"""
app/agent/tools/
==================
Tool registries for the AI OS layer, one module per business domain
(billing_tools.py, inventory_tools.py, finance_tools.py, migration_tools.py,
security_tools.py, analytics_tools.py). Each module exposes a list of
ToolDefinition entries — name, description, JSON-schema input_schema,
required_permission, and a handler function.

As of the 5-copilot consolidation, callers should not assemble this list
themselves — app.agent.orchestrator.loop.get_tools_for_user(tenant_id,
user_id, db) is the single source of truth: it merges every module below
(_ALL_TOOL_MODULES in loop.py) and filters to only the tools this user's
RBAC permissions allow, BEFORE the list is ever sent to the model. Passing
an explicit `tools=` list to run_turn()/resume_after_confirmation() (e.g.
in tests) bypasses that merge+filter entirely — only do so deliberately.

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

from app.agent.tools.analytics_tools import ANALYTICS_TOOLS
from app.agent.tools.base import ToolDefinition
from app.agent.tools.billing_tools import BILLING_TOOLS
from app.agent.tools.finance_tools import FINANCE_TOOLS
from app.agent.tools.inventory_tools import INVENTORY_TOOLS
from app.agent.tools.migration_tools import MIGRATION_TOOLS
from app.agent.tools.security_tools import SECURITY_TOOLS

__all__ = [
    "BILLING_TOOLS", "INVENTORY_TOOLS", "FINANCE_TOOLS", "MIGRATION_TOOLS",
    "SECURITY_TOOLS", "ANALYTICS_TOOLS", "ToolDefinition",
]
