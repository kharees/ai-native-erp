"""
app/agent/tools/analytics_tools.py
=====================================
Third tool registry for the AI OS layer (audit #3): 5 read-only,
non-confirmation-gated LLM-callable tools over existing Billing/Inventory
data. Follows the same contract as app/agent/tools/billing_tools.py/
inventory_tools.py -- see billing_tools.py's docstring for the full
rationale (tenant_id never in input_schema, unit-of-work via db_session()).

None of these require_confirmation -- they're pure reads, nothing to
confirm. None need idempotency_key either, for the same reason.

Every number here comes from a real SQL aggregation against the actual
Billing/Inventory tables -- never computed, estimated, or invented by the
model. See app/agent/orchestrator/loop.py's ANALYTICS_SYSTEM_PROMPT_ADDITION,
which instructs the model to only narrate what these tools return.

Deliberately NOT reusing app/crud/universal_analytics.py's
get_sales_summary/get_leaderboards/get_financial_summary for this: those
three contain hardcoded/mock data (fabricated trend points, a hardcoded
"Premium Widget" leaderboard entry, an invented 18% tax assumption, and
aging buckets computed as arbitrary percentages of total revenue rather
than real per-invoice aging) -- exactly the "don't let the model narrate
fabricated numbers" failure mode this tool registry exists to avoid. Fresh,
real SQL below instead, styled after that same file's honest functions
(get_valuation_summary, get_abc_analysis, get_aging_report).

Two real data gaps, both worked around with a documented, unavoidable
fallback (no viable alternative exists, so not a design choice to weigh):
  - No reorder_level/reorder-point field exists anywhere on UniversalItemMaster
    or UniversalStockBalance (same gap already found and documented for
    app/services/universal_intelligence.py). get_low_stock_items uses the
    caller-supplied `threshold` (defaulting to 0 -- "at or below zero
    available") instead of a true reorder point.
  - No due_date field exists on UniversalTaxInvoice. get_outstanding_dues'
    aging buckets are computed from invoice age (days since created_at),
    not true days-overdue.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import ToolDefinition
from app.core.database import db_session
from app.models.universal_customers import UniversalCustomer
from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_invoices import UniversalTaxInvoice, UniversalTaxInvoiceItem
from app.models.universal_payments import UniversalPaymentAllocation
from app.models.universal_warehousing import UniversalStockBalance
from app.services.agent_adapters.base import agent_tool

_ISSUED = "ISSUED"


def _date_range_filter(column, date_from: date, date_to: date):
    return cast(column, Date).between(date_from, date_to)


# ---------------------------------------------------------------------------
# get_sales_summary
# ---------------------------------------------------------------------------

_GET_SALES_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "date_from": {"type": "string", "format": "date"},
        "date_to": {"type": "string", "format": "date"},
    },
    "required": ["date_from", "date_to"],
}


@agent_tool
async def handle_get_sales_summary(
    tenant_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> dict[str, Any]:
    async with db_session() as db:
        stmt = select(
            func.coalesce(func.sum(UniversalTaxInvoice.total_amount), 0),
            func.count(UniversalTaxInvoice.id),
        ).where(
            UniversalTaxInvoice.tenant_id == tenant_id,
            UniversalTaxInvoice.status == _ISSUED,
            _date_range_filter(UniversalTaxInvoice.created_at, date_from, date_to),
        )
        total_sales, invoice_count = (await db.execute(stmt)).one()
        total_sales = float(total_sales or 0)
        invoice_count = invoice_count or 0
        average_invoice_value = (total_sales / invoice_count) if invoice_count > 0 else 0.0

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "total_sales_value": total_sales,
            "invoice_count": invoice_count,
            "average_invoice_value": average_invoice_value,
        }


# ---------------------------------------------------------------------------
# get_top_items
# ---------------------------------------------------------------------------

_GET_TOP_ITEMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "date_from": {"type": "string", "format": "date"},
        "date_to": {"type": "string", "format": "date"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
    },
    "required": ["date_from", "date_to"],
}


@agent_tool
async def handle_get_top_items(
    tenant_id: uuid.UUID,
    date_from: date,
    date_to: date,
    limit: int = 10,
) -> dict[str, Any]:
    async with db_session() as db:
        base_stmt = (
            select(
                UniversalTaxInvoiceItem.item_id,
                UniversalItemMaster.name,
                func.sum(UniversalTaxInvoiceItem.quantity).label("total_quantity"),
                func.sum(UniversalTaxInvoiceItem.line_total).label("total_value"),
            )
            .join(UniversalTaxInvoice, UniversalTaxInvoice.id == UniversalTaxInvoiceItem.invoice_id)
            .join(UniversalItemMaster, UniversalItemMaster.id == UniversalTaxInvoiceItem.item_id)
            .where(
                UniversalTaxInvoiceItem.tenant_id == tenant_id,
                UniversalTaxInvoice.status == _ISSUED,
                _date_range_filter(UniversalTaxInvoice.created_at, date_from, date_to),
            )
            .group_by(UniversalTaxInvoiceItem.item_id, UniversalItemMaster.name)
        )

        by_quantity_rows = (await db.execute(base_stmt.order_by(func.sum(UniversalTaxInvoiceItem.quantity).desc()).limit(limit))).all()
        by_value_rows = (await db.execute(base_stmt.order_by(func.sum(UniversalTaxInvoiceItem.line_total).desc()).limit(limit))).all()

        def _row(r) -> dict[str, Any]:
            return {
                "item_id": str(r.item_id),
                "item_name": r.name,
                "total_quantity": float(r.total_quantity),
                "total_value": float(r.total_value),
            }

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "by_quantity": [_row(r) for r in by_quantity_rows],
            "by_value": [_row(r) for r in by_value_rows],
        }


# ---------------------------------------------------------------------------
# get_low_stock_items
# ---------------------------------------------------------------------------

_GET_LOW_STOCK_ITEMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "threshold": {
            "type": "number",
            "description": (
                "Items with available quantity (on-hand minus reserved "
                "minus allocated) at or below this are returned. Defaults "
                "to 0 -- this system has no reorder-point field, so 0 is "
                "the only universally meaningful default."
            ),
        },
    },
    "required": [],
}


@agent_tool
async def handle_get_low_stock_items(
    tenant_id: uuid.UUID,
    threshold: float | None = None,
) -> dict[str, Any]:
    effective_threshold = threshold if threshold is not None else 0.0
    async with db_session() as db:
        available = (
            UniversalStockBalance.quantity_on_hand
            - UniversalStockBalance.quantity_reserved
            - UniversalStockBalance.quantity_allocated
        )
        stmt = (
            select(
                UniversalStockBalance.item_id,
                UniversalItemMaster.name,
                UniversalStockBalance.warehouse_id,
                available.label("available_quantity"),
            )
            .join(UniversalItemMaster, UniversalItemMaster.id == UniversalStockBalance.item_id)
            .where(
                UniversalStockBalance.tenant_id == tenant_id,
                available <= effective_threshold,
            )
            .order_by(available.asc())
        )
        rows = (await db.execute(stmt)).all()

        return {
            "threshold": effective_threshold,
            "items": [
                {
                    "item_id": str(r.item_id),
                    "item_name": r.name,
                    "warehouse_id": str(r.warehouse_id),
                    "available_quantity": float(r.available_quantity),
                }
                for r in rows
            ],
        }


# ---------------------------------------------------------------------------
# get_outstanding_dues
# ---------------------------------------------------------------------------

_GET_OUTSTANDING_DUES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_id": {"type": "string", "format": "uuid"},
    },
    "required": [],
}


def _aging_bucket(days: int) -> str:
    if days <= 30:
        return "0-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    return "90+"


@agent_tool
async def handle_get_outstanding_dues(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    async with db_session() as db:
        paid_subq = (
            select(
                UniversalPaymentAllocation.invoice_id.label("invoice_id"),
                func.sum(UniversalPaymentAllocation.allocated_amount).label("paid_amount"),
            )
            .where(UniversalPaymentAllocation.tenant_id == tenant_id)
            .group_by(UniversalPaymentAllocation.invoice_id)
            .subquery()
        )

        stmt = (
            select(
                UniversalTaxInvoice.id,
                UniversalTaxInvoice.invoice_number,
                UniversalTaxInvoice.customer_id,
                UniversalCustomer.name,
                UniversalTaxInvoice.total_amount,
                UniversalTaxInvoice.created_at,
                func.coalesce(paid_subq.c.paid_amount, 0).label("paid_amount"),
            )
            .join(UniversalCustomer, UniversalCustomer.id == UniversalTaxInvoice.customer_id)
            .outerjoin(paid_subq, paid_subq.c.invoice_id == UniversalTaxInvoice.id)
            .where(
                UniversalTaxInvoice.tenant_id == tenant_id,
                UniversalTaxInvoice.status == _ISSUED,
            )
        )
        if customer_id is not None:
            stmt = stmt.where(UniversalTaxInvoice.customer_id == customer_id)

        rows = (await db.execute(stmt)).all()
        now = datetime.now(timezone.utc)

        outstanding: list[dict[str, Any]] = []
        bucket_totals = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
        for r in rows:
            balance_due = float(r.total_amount) - float(r.paid_amount)
            if balance_due <= 0:
                continue
            created_at = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc)
            days_outstanding = (now - created_at).days
            bucket = _aging_bucket(days_outstanding)
            bucket_totals[bucket] += balance_due
            outstanding.append({
                "invoice_id": str(r.id),
                "invoice_number": r.invoice_number,
                "customer_id": str(r.customer_id),
                "customer_name": r.name,
                "total_amount": float(r.total_amount),
                "paid_amount": float(r.paid_amount),
                "balance_due": balance_due,
                "days_outstanding": days_outstanding,
                "aging_bucket": bucket,
            })

        return {
            "invoices": outstanding,
            "total_outstanding": sum(bucket_totals.values()),
            "aging_buckets": bucket_totals,
        }


# ---------------------------------------------------------------------------
# get_customer_summary
# ---------------------------------------------------------------------------

_GET_CUSTOMER_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_id": {"type": "string", "format": "uuid"},
        "date_from": {"type": "string", "format": "date"},
        "date_to": {"type": "string", "format": "date"},
    },
    "required": ["customer_id", "date_from", "date_to"],
}


@agent_tool
async def handle_get_customer_summary(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> dict[str, Any]:
    async with db_session() as db:
        paid_subq = (
            select(
                UniversalPaymentAllocation.invoice_id.label("invoice_id"),
                func.sum(UniversalPaymentAllocation.allocated_amount).label("paid_amount"),
            )
            .where(UniversalPaymentAllocation.tenant_id == tenant_id)
            .group_by(UniversalPaymentAllocation.invoice_id)
            .subquery()
        )

        stmt = (
            select(
                UniversalTaxInvoice.id,
                UniversalTaxInvoice.invoice_number,
                UniversalTaxInvoice.status,
                UniversalTaxInvoice.total_amount,
                UniversalTaxInvoice.created_at,
                func.coalesce(paid_subq.c.paid_amount, 0).label("paid_amount"),
            )
            .outerjoin(paid_subq, paid_subq.c.invoice_id == UniversalTaxInvoice.id)
            .where(
                UniversalTaxInvoice.tenant_id == tenant_id,
                UniversalTaxInvoice.customer_id == customer_id,
                _date_range_filter(UniversalTaxInvoice.created_at, date_from, date_to),
            )
            .order_by(UniversalTaxInvoice.created_at.desc())
        )
        rows = (await db.execute(stmt)).all()

        orders = []
        total_spend = 0.0
        total_paid = 0.0
        for r in rows:
            paid_amount = float(r.paid_amount)
            total_amount = float(r.total_amount)
            if r.status == _ISSUED:
                total_spend += total_amount
                total_paid += paid_amount
            orders.append({
                "invoice_id": str(r.id),
                "invoice_number": r.invoice_number,
                "status": r.status,
                "total_amount": total_amount,
                "paid_amount": paid_amount,
                "balance_due": total_amount - paid_amount,
                "created_at": r.created_at.isoformat(),
            })

        return {
            "customer_id": str(customer_id),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "order_count": len(orders),
            "total_spend": total_spend,
            "total_paid": total_paid,
            "total_outstanding": total_spend - total_paid,
            "orders": orders,
        }


ANALYTICS_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="get_sales_summary",
        description=(
            "Total sales value, invoice count, and average invoice value "
            "for a date range, from real issued invoices."
        ),
        input_schema=_GET_SALES_SUMMARY_SCHEMA,
        required_permission=("UniversalBilling", "Analytics", "Read"),
        handler=handle_get_sales_summary,
    ),
    ToolDefinition(
        name="get_top_items",
        description=(
            "Best-selling items for a date range, ranked separately by "
            "quantity sold and by sales value."
        ),
        input_schema=_GET_TOP_ITEMS_SCHEMA,
        required_permission=("UniversalBilling", "Analytics", "Read"),
        handler=handle_get_top_items,
    ),
    ToolDefinition(
        name="get_low_stock_items",
        description=(
            "Items at or below a stock threshold (available quantity = "
            "on-hand minus reserved minus allocated). No reorder-point "
            "field exists in this system, so threshold defaults to 0."
        ),
        input_schema=_GET_LOW_STOCK_ITEMS_SCHEMA,
        required_permission=("UniversalInventory", "Stock", "Read"),
        handler=handle_get_low_stock_items,
    ),
    ToolDefinition(
        name="get_outstanding_dues",
        description=(
            "Unpaid or partially paid issued invoices with aging buckets "
            "(0-30, 31-60, 61-90, 90+ days since the invoice was raised). "
            "Optionally scoped to one customer."
        ),
        input_schema=_GET_OUTSTANDING_DUES_SCHEMA,
        required_permission=("UniversalBilling", "Analytics", "Read"),
        handler=handle_get_outstanding_dues,
    ),
    ToolDefinition(
        name="get_customer_summary",
        description=(
            "One customer's order history, total spend, and payment "
            "status for a date range."
        ),
        input_schema=_GET_CUSTOMER_SUMMARY_SCHEMA,
        required_permission=("UniversalBilling", "Analytics", "Read"),
        handler=handle_get_customer_summary,
    ),
]
