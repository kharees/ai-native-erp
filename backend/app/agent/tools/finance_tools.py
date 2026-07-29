"""
app/agent/tools/finance_tools.py
===================================
Finance tools for the consolidated AI orchestrator (app/agent/orchestrator/
loop.py) -- follows the exact same contract as app/agent/tools/
billing_tools.py. See that file's docstring for the full rationale
(tenant_id never in input_schema, unit-of-work via db_session()).

Consolidation note: app/services/finance_ai_copilot.py previously also had
process_chat_query and scan_for_fraud_and_risks -- both were removed
entirely (not converted), since both were 100% hardcoded fabricated
output (canned P&L/receivables/cash-flow text keyed off prompt keywords;
two fake "detected" fraud incidents with invented dollar amounts), not
real analysis. get_finance_insights below wraps that file's one genuine
function -- a real query against the AIFinanceInsight table.

get_customer_credit_risk/get_fraud_alerts wrap app/crud/universal_ai_billing.py
(the service backing the old omnichannel-billing ai-copilot page, not one
of the 4 files originally named for conversion, but that page itself was
named for replacement) -- calculate_credit_risk is real (grounded customer/
invoice queries, risk_score is a real deterministic calculation from real
data, not fabricated, just a simple heuristic formula) and
scan_fraud_anomalies is a real query against UniversalAIFraudAlert. That
same file's generate_smart_draft was NOT converted -- 100% hardcoded fake
product suggestions ("Premium Bundle Add-on" @ $99.99 regardless of input),
and wasn't even used by the page being replaced.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.agent.tools.base import ToolDefinition
from app.core.database import db_session
from app.crud import universal_ai_billing as crud_ai_billing
from app.services.finance_ai_copilot import finance_ai_service
from app.services.agent_adapters.base import agent_tool

_GET_FINANCE_INSIGHTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
    },
    "required": [],
}


@agent_tool
async def handle_get_finance_insights(
    tenant_id: uuid.UUID,
    limit: int = 50,
) -> dict[str, Any]:
    # Read-only: no user_id, no idempotency concern.
    async with db_session() as db:
        insights = await finance_ai_service.get_insights(db, tenant_id=tenant_id, skip=0, limit=limit)
        return {
            "insights": [
                {
                    "id": str(i.id),
                    "insight_type": i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "severity": i.severity,
                    "confidence_score": float(i.confidence_score),
                    "status": i.status,
                }
                for i in insights
            ],
            "total": len(insights),
        }


_GET_CUSTOMER_CREDIT_RISK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"customer_id": {"type": "string", "format": "uuid"}},
    "required": ["customer_id"],
}


@agent_tool
async def handle_get_customer_credit_risk(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> dict[str, Any]:
    async with db_session() as db:
        result = await crud_ai_billing.calculate_credit_risk(db, tenant_id, customer_id)
        if result is None:
            return {"error": True, "detail": "Customer not found."}
        return result.model_dump(mode="json")


_GET_FRAUD_ALERTS_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}, "required": []}


@agent_tool
async def handle_get_fraud_alerts(tenant_id: uuid.UUID) -> dict[str, Any]:
    async with db_session() as db:
        alerts = await crud_ai_billing.scan_fraud_anomalies(db, tenant_id)
        return {
            "alerts": [
                {
                    "id": str(a.id),
                    "customer_id": str(a.customer_id) if a.customer_id else None,
                    "invoice_id": str(a.invoice_id) if a.invoice_id else None,
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "alert_details": a.alert_details,
                    "status": a.status,
                }
                for a in alerts
            ],
            "total": len(alerts),
        }


FINANCE_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="get_finance_insights",
        description=(
            "Retrieve previously generated finance insights/alerts (risk, "
            "compliance, forecast items) for this tenant, most recent first."
        ),
        input_schema=_GET_FINANCE_INSIGHTS_SCHEMA,
        required_permission=("Finance", "AICopilot", "Read"),
        handler=handle_get_finance_insights,
    ),
    ToolDefinition(
        name="get_customer_credit_risk",
        description="Real, data-grounded credit risk score (0-100) and recommended credit limit for one customer.",
        input_schema=_GET_CUSTOMER_CREDIT_RISK_SCHEMA,
        required_permission=("UniversalBilling", "AI", "Read"),
        handler=handle_get_customer_credit_risk,
    ),
    ToolDefinition(
        name="get_fraud_alerts",
        description="Open (unresolved) fraud/anomaly alerts for this tenant's billing activity.",
        input_schema=_GET_FRAUD_ALERTS_SCHEMA,
        required_permission=("UniversalBilling", "AI", "Read"),
        handler=handle_get_fraud_alerts,
    ),
]
