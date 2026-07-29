"""
app/agent/tools/security_tools.py
====================================
Identity/Security tools for the consolidated AI orchestrator
(app/agent/orchestrator/loop.py) -- follows the exact same contract as
app/agent/tools/billing_tools.py. See that file's docstring for the full
rationale (tenant_id never in input_schema, unit-of-work via db_session()).

New module, not one of the three the original consolidation ask named
(finance/inventory/migration) -- app/services/ai_intelligence.py is
Identity/Security, a distinct domain that doesn't map to any of those
three, so it gets its own tool file rather than being folded into an
unrelated one.

Consolidation note: ai_intelligence.py previously also had
get_role_recommendations (100% hardcoded fake employees/UUIDs) and
AuditAnalyzer.query_natural_language (100% hardcoded fabricated audit
narrative) -- both removed entirely, not converted, since neither had any
real logic underneath. calculate_org_risk_score's fabricated "impossible
travel" incident (hardcoded, asserted for every tenant) was also removed;
its two real heuristics (brute-force/privilege-escalation counts) remain
and back get_org_risk_score below.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.agent.tools.base import ToolDefinition
from app.core.database import db_session
from app.services.ai_intelligence import IdentityAnalyzer, SecurityAnalyzer
from app.services.agent_adapters.base import agent_tool

_GET_INACTIVE_USERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "days_inactive": {"type": "integer", "minimum": 1, "default": 30},
    },
    "required": [],
}


@agent_tool
async def handle_get_inactive_users(
    tenant_id: uuid.UUID,
    days_inactive: int = 30,
) -> dict[str, Any]:
    async with db_session() as db:
        inactive = await IdentityAnalyzer.get_inactive_users(db, tenant_id, days_inactive)
        return {"inactive_users": inactive, "total": len(inactive)}


_GET_ORG_RISK_SCORE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "required": [],
}


@agent_tool
async def handle_get_org_risk_score(tenant_id: uuid.UUID) -> dict[str, Any]:
    async with db_session() as db:
        return await SecurityAnalyzer.calculate_org_risk_score(db, tenant_id)


SECURITY_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="get_inactive_users",
        description="List users who haven't logged in within the given number of days (default 30).",
        input_schema=_GET_INACTIVE_USERS_SCHEMA,
        required_permission=("RBAC", "Roles", "Read"),
        handler=handle_get_inactive_users,
    ),
    ToolDefinition(
        name="get_org_risk_score",
        description=(
            "Real-time organization security score (0-100) based on recent "
            "brute-force login attempts and privilege-escalation activity."
        ),
        input_schema=_GET_ORG_RISK_SCORE_SCHEMA,
        required_permission=("Audit", "Logs", "Read"),
        handler=handle_get_org_risk_score,
    ),
]
