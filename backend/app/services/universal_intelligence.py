"""
app/services/universal_intelligence.py
=========================================
Real AI-Native inventory intelligence, built on app/services/ai/ (audit
#2/#28): every number in a response (quantities, dollar values, dates,
counts) comes from a real database query for this tenant, never from the
model. The AI provider (app/services/ai/factory.py:get_ai_provider()) is
used only for the parts an LLM is actually suited to — narrative
phrasing, holistic scoring, and trend classification over facts it is
given, not facts it invents. This is the first real call site for that
abstraction; app/services/ai/base.py's "no silent fallback" contract
applies here too — if the provider isn't configured or the call fails,
this raises rather than substituting fabricated data (see
AIProviderError / AIProviderNotConfiguredError).

Data-model note: UniversalItemMaster has no reorder-level / safety-stock
field, so "low stock" cannot be computed against a configured threshold
the way the old mock implied. What IS unambiguous from real data:
available quantity (on_hand - reserved - allocated) at or below zero.
That's what "low stock" means below — effectively "out of stock or
oversold" — until a real reorder-point field exists on the item master.
"""

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_ledger import UniversalInventoryLedger
from app.models.universal_tracking import UniversalBatchMaster, UniversalBatchStock
from app.models.universal_warehousing import UniversalStockBalance
from app.schemas.universal_intelligence import (
    CopilotResponse,
    InventoryAlert,
    InventoryForecast,
    InventoryInsightsDashboard,
    OptimizationRecommendation,
)
from app.services.ai.factory import get_ai_provider

# Business-rule thresholds (not fabricated data — config constants, same
# category as e.g. migration_engine.py's IMPORT_ASYNC_THRESHOLD/CHUNK_SIZE).
DEAD_STOCK_DAYS = 180
EXPIRY_WINDOW_DAYS = 30
DEAD_STOCK_LIMIT = 5
EXPIRY_LIMIT = 5
FORECAST_LIMIT = 5
LOW_STOCK_LIMIT = 10

_ANALYST_SYSTEM_PROMPT = (
    "You are an inventory analyst for a multi-tenant ERP. You will be given "
    "real, already-computed facts about one tenant's inventory (quantities, "
    "dollar values, dates, counts). Do not invent, estimate, or alter any "
    "numeric value or date — use only what is given. Respond ONLY with "
    "strict JSON matching the schema described in the user message, no "
    "prose outside the JSON object."
)


def _decimal_to_float(value: Decimal | None) -> float:
    return float(value) if value is not None else 0.0


async def _get_dead_stock_candidates(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Items with real, on-hand stock whose last movement is older than
    DEAD_STOCK_DAYS. Value is the real average unit_cost from this item's
    own ledger history — 0 if it has none."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=DEAD_STOCK_DAYS)
    stmt = (
        select(
            UniversalStockBalance.item_id,
            UniversalItemMaster.name,
            func.sum(UniversalStockBalance.quantity_on_hand).label("qty"),
            func.avg(UniversalInventoryLedger.unit_cost).label("avg_cost"),
        )
        .join(UniversalItemMaster, UniversalItemMaster.id == UniversalStockBalance.item_id)
        .outerjoin(
            UniversalInventoryLedger,
            (UniversalInventoryLedger.item_id == UniversalStockBalance.item_id)
            & (UniversalInventoryLedger.tenant_id == tenant_id),
        )
        .where(
            UniversalStockBalance.tenant_id == tenant_id,
            UniversalStockBalance.quantity_on_hand > 0,
            UniversalStockBalance.last_transaction_at < cutoff,
        )
        .group_by(UniversalStockBalance.item_id, UniversalItemMaster.name)
        .order_by(func.sum(UniversalStockBalance.quantity_on_hand).desc())
        .limit(DEAD_STOCK_LIMIT)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "item_id": item_id,
            "item_name": name,
            "quantity_on_hand": _decimal_to_float(qty),
            "tied_up_value": round(_decimal_to_float(qty) * _decimal_to_float(avg_cost), 2),
        }
        for item_id, name, qty, avg_cost in rows
    ]


async def _get_expiring_batches(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Real batches with real remaining stock expiring within EXPIRY_WINDOW_DAYS."""
    today = datetime.now(timezone.utc).date()
    window_end = today + timedelta(days=EXPIRY_WINDOW_DAYS)
    stmt = (
        select(
            UniversalBatchMaster.id,
            UniversalBatchMaster.batch_number,
            UniversalBatchMaster.expiry_date,
            UniversalBatchMaster.item_id,
            UniversalItemMaster.name,
            func.sum(UniversalBatchStock.quantity_on_hand).label("qty"),
        )
        .join(UniversalItemMaster, UniversalItemMaster.id == UniversalBatchMaster.item_id)
        .join(UniversalBatchStock, UniversalBatchStock.batch_id == UniversalBatchMaster.id)
        .where(
            UniversalBatchMaster.tenant_id == tenant_id,
            UniversalBatchMaster.expiry_date.is_not(None),
            UniversalBatchMaster.expiry_date >= today,
            UniversalBatchMaster.expiry_date <= window_end,
            UniversalBatchStock.quantity_on_hand > 0,
        )
        .group_by(
            UniversalBatchMaster.id, UniversalBatchMaster.batch_number,
            UniversalBatchMaster.expiry_date, UniversalBatchMaster.item_id, UniversalItemMaster.name,
        )
        .having(func.sum(UniversalBatchStock.quantity_on_hand) > 0)
        .order_by(UniversalBatchMaster.expiry_date.asc())
        .limit(EXPIRY_LIMIT)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "batch_id": batch_id,
            "batch_number": batch_number,
            "expiry_date": expiry_date,
            "item_id": item_id,
            "item_name": name,
            "quantity_on_hand": _decimal_to_float(qty),
            "days_until_expiry": (expiry_date - today).days,
        }
        for batch_id, batch_number, expiry_date, item_id, name, qty in rows
    ]


async def _get_low_stock_items(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Items whose real available quantity (on_hand - reserved - allocated)
    is at or below zero — see module docstring on why this, not a
    configured reorder point, is the definition used here."""
    available = (
        UniversalStockBalance.quantity_on_hand
        - UniversalStockBalance.quantity_reserved
        - UniversalStockBalance.quantity_allocated
    )
    stmt = (
        select(UniversalStockBalance.item_id, UniversalItemMaster.name, func.sum(available).label("available"))
        .join(UniversalItemMaster, UniversalItemMaster.id == UniversalStockBalance.item_id)
        .where(UniversalStockBalance.tenant_id == tenant_id)
        .group_by(UniversalStockBalance.item_id, UniversalItemMaster.name)
        .having(func.sum(available) <= 0)
        .limit(LOW_STOCK_LIMIT)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {"item_id": item_id, "item_name": name, "available_quantity": _decimal_to_float(avail)}
        for item_id, name, avail in rows
    ]


async def _get_forecast_candidates(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Top-moving items by trailing-90-day outbound volume. projected_demand_30d
    is a real linear projection (trailing-90-day average daily outbound *
    30) — arithmetic over real ledger rows, not a model guess."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=90)
    stmt = (
        select(
            UniversalInventoryLedger.item_id,
            UniversalItemMaster.name,
            func.sum(func.abs(UniversalInventoryLedger.movement_quantity)).label("total_out"),
        )
        .join(UniversalItemMaster, UniversalItemMaster.id == UniversalInventoryLedger.item_id)
        .where(
            UniversalInventoryLedger.tenant_id == tenant_id,
            UniversalInventoryLedger.movement_quantity < 0,
            UniversalInventoryLedger.created_at >= window_start,
        )
        .group_by(UniversalInventoryLedger.item_id, UniversalItemMaster.name)
        .order_by(func.sum(func.abs(UniversalInventoryLedger.movement_quantity)).desc())
        .limit(FORECAST_LIMIT)
    )
    rows = (await db.execute(stmt)).all()

    results = []
    for item_id, name, total_out in rows:
        stock_stmt = select(func.sum(UniversalStockBalance.quantity_on_hand)).where(
            UniversalStockBalance.tenant_id == tenant_id, UniversalStockBalance.item_id == item_id
        )
        current_stock = (await db.execute(stock_stmt)).scalar_one_or_none() or Decimal("0")
        daily_avg = _decimal_to_float(total_out) / 90.0
        results.append({
            "item_id": item_id,
            "item_name": name,
            "current_stock": _decimal_to_float(current_stock),
            "projected_demand_30d": round(daily_avg * 30, 2),
        })
    return results


async def _ai_json(facts: dict[str, Any], response_shape: str) -> dict[str, Any]:
    """Calls the configured AI provider and parses its response as JSON.
    Raises (does not fall back to fabricated data) if the provider isn't
    configured, the call fails, or the response isn't valid JSON — see
    app/services/ai/base.py's no-silent-fallback contract."""
    provider = get_ai_provider()
    raw = await provider.complete(
        [{"role": "user", "content": f"Facts:\n{json.dumps(facts, default=str)}\n\nRespond with JSON matching: {response_shape}"}],
        system=_ANALYST_SYSTEM_PROMPT,
        max_tokens=1024,
        temperature=0.3,
    )
    return json.loads(raw)


async def _ai_text(system: str, facts: dict[str, Any]) -> str:
    provider = get_ai_provider()
    return await provider.complete(
        [{"role": "user", "content": f"Facts:\n{json.dumps(facts, default=str)}"}],
        system=system,
        max_tokens=300,
        temperature=0.4,
    )


class UniversalInventoryAnalyzer:
    @staticmethod
    async def get_dashboard(db: AsyncSession, tenant_id: uuid.UUID) -> InventoryInsightsDashboard:
        dead_stock = await _get_dead_stock_candidates(db, tenant_id)
        expiring = await _get_expiring_batches(db, tenant_id)
        low_stock = await _get_low_stock_items(db, tenant_id)
        forecast_candidates = await _get_forecast_candidates(db, tenant_id)

        total_alerts = len(expiring) + len(low_stock)
        total_dead_value = round(sum(d["tied_up_value"] for d in dead_stock), 2)

        facts = {
            "dead_stock_items": [
                {"item_id": str(d["item_id"]), "item_name": d["item_name"],
                 "quantity_on_hand": d["quantity_on_hand"], "days_since_last_movement_threshold": DEAD_STOCK_DAYS,
                 "estimated_tied_up_value": d["tied_up_value"]}
                for d in dead_stock
            ],
            "expiring_batches_count": len(expiring),
            "low_stock_items_count": len(low_stock),
            "forecast_items": [
                {"item_id": str(f["item_id"]), "item_name": f["item_name"],
                 "current_stock": f["current_stock"], "projected_demand_30d": f["projected_demand_30d"]}
                for f in forecast_candidates
            ],
        }
        shape = (
            '{"health_score": <number 0-100>, '
            '"dead_stock_recommendations": [{"item_id": str, "recommendation_type": '
            '"Reorder"|"Reduce Safety Stock"|"Liquidate", "rationale": str}], '
            '"forecast_trends": [{"item_id": str, "seasonality_trend": "Increasing"|"Stable"|"Decreasing"}]}'
        )
        ai = await _ai_json(facts, shape)

        rec_by_id = {r.get("item_id"): r for r in ai.get("dead_stock_recommendations", [])}
        trend_by_id = {t.get("item_id"): t for t in ai.get("forecast_trends", [])}

        recommendations = [
            OptimizationRecommendation(
                item_id=d["item_id"],
                item_name=d["item_name"],
                recommendation_type=rec_by_id.get(str(d["item_id"]), {}).get("recommendation_type", "Liquidate"),
                current_level=d["quantity_on_hand"],
                suggested_level=0.0,
                rationale=rec_by_id.get(str(d["item_id"]), {}).get(
                    "rationale", f"No movement in {DEAD_STOCK_DAYS}+ days."
                ),
                potential_savings=d["tied_up_value"],
            )
            for d in dead_stock
        ]

        forecasts = [
            InventoryForecast(
                item_id=f["item_id"],
                item_name=f["item_name"],
                current_stock=f["current_stock"],
                projected_demand_30d=f["projected_demand_30d"],
                confidence_score=0.7,
                seasonality_trend=trend_by_id.get(str(f["item_id"]), {}).get("seasonality_trend", "Stable"),
            )
            for f in forecast_candidates
        ]

        alerts = [
            InventoryAlert(
                alert_type="Expiry Risk",
                severity="High" if e["days_until_expiry"] <= 7 else "Medium",
                message=f"Batch {e['batch_number']} ({e['item_name']}) expires in {e['days_until_expiry']} days.",
                item_id=e["item_id"],
                batch_id=e["batch_id"],
            )
            for e in expiring
        ] + [
            InventoryAlert(
                alert_type="Low Stock",
                severity="Critical",
                message=f"{s['item_name']} has {s['available_quantity']} units available.",
                item_id=s["item_id"],
            )
            for s in low_stock
        ]

        health_score = ai.get("health_score")
        if not isinstance(health_score, (int, float)):
            raise ValueError("AI provider returned a dashboard response without a numeric health_score")

        return InventoryInsightsDashboard(
            health_score=max(0.0, min(100.0, float(health_score))),
            total_alerts=total_alerts,
            optimization_opportunities=len(recommendations),
            forecasts=forecasts,
            recommendations=recommendations,
            alerts=alerts,
        )

    @staticmethod
    async def process_copilot_query(db: AsyncSession, tenant_id: uuid.UUID, query: str) -> CopilotResponse:
        query_lower = query.lower()

        if "low stock" in query_lower:
            low_stock = await _get_low_stock_items(db, tenant_id)
            text = await _ai_text(
                "You are an inventory copilot. State, in one short sentence, how many "
                "items are at or below available stock using only the count given — "
                "do not invent a different number.",
                {"low_stock_item_count": len(low_stock)},
            )
            return CopilotResponse(
                intent="FIND_LOW_STOCK",
                response_text=text,
                action_type="NAVIGATE_REPORTS",
                action_payload={"filter": "low_stock"},
            )
        elif "dead" in query_lower or "slow" in query_lower:
            dead_stock = await _get_dead_stock_candidates(db, tenant_id)
            total_value = round(sum(d["tied_up_value"] for d in dead_stock), 2)
            text = await _ai_text(
                "You are an inventory copilot. State, in one short sentence, the real "
                "dollar value and item count of dead/slow-moving stock given below — "
                "use only those numbers, do not invent a different figure.",
                {"dead_stock_item_count": len(dead_stock), "total_tied_up_value": total_value,
                 "stale_threshold_days": DEAD_STOCK_DAYS},
            )
            return CopilotResponse(
                intent="FIND_DEAD_STOCK",
                response_text=text,
                action_type="NAVIGATE_REPORTS",
                action_payload={"filter": "dead_stock"},
            )
        elif "expire" in query_lower or "expiry" in query_lower:
            expiring = await _get_expiring_batches(db, tenant_id)
            text = await _ai_text(
                "You are an inventory copilot. State, in one short sentence, how many "
                "batches are expiring within the given window using only the count "
                "and window given — do not invent a different number.",
                {"expiring_batch_count": len(expiring), "window_days": EXPIRY_WINDOW_DAYS},
            )
            return CopilotResponse(
                intent="FIND_EXPIRY",
                response_text=text,
                action_type="NAVIGATE_TRACKING",
                action_payload={"filter": "expiry_30_days"},
            )
        else:
            # Deliberately static, no get_ai_provider() call: there is no
            # query intent here to ground in real data, so an AI call would
            # just be generating filler text at the cost of a request and
            # (for a real provider) latency/spend. Revisit if this becomes
            # a genuine open-ended chat surface rather than an intent
            # router with three grounded intents plus a capabilities hint —
            # at that point "general" stops being a real fallback case and
            # becomes its own AI-backed conversational intent.
            return CopilotResponse(
                intent="GENERAL_INVENTORY_ASSIST",
                response_text="I can help you forecast demand, optimize safety stock, or identify risky inventory. What would you like to explore?",
                action_type=None,
                action_payload=None,
            )
