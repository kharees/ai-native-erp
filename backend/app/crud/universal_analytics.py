import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_invoices import UniversalTaxInvoice
from app.models.universal_customers import UniversalCustomer
from app.models.universal_payments import UniversalPaymentReceipt
from app.models.universal_warehousing import UniversalStockBalance
from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_ledger import UniversalInventoryLedger
from app.schemas.universal_analytics import (
    SalesSummaryResponse, SalesTrendPoint,
    AnalyticsLeaderboardResponse, AnalyticsLeaderboardItem,
    FinancialSummaryResponse
)
from app.schemas.universal_reports import StockValuationSummary

async def get_sales_summary(db: AsyncSession, tenant_id: uuid.UUID, period: str) -> SalesSummaryResponse:
    # Dummy mock logic for Phase 5 proof of concept structure. 
    # In production, we group by func.date_trunc('day', UniversalTaxInvoice.created_at)
    stmt = select(func.sum(UniversalTaxInvoice.total_amount), func.count(UniversalTaxInvoice.id)).where(
        UniversalTaxInvoice.tenant_id == tenant_id,
        UniversalTaxInvoice.status == 'ISSUED'
    )
    result = await db.execute(stmt)
    total_rev, total_orders = result.fetchone()
    total_rev = float(total_rev or 0)
    total_orders = total_orders or 0
    aov = (total_rev / total_orders) if total_orders > 0 else 0

    return SalesSummaryResponse(
        total_revenue=total_rev,
        total_orders=total_orders,
        average_order_value=aov,
        trends=[
            SalesTrendPoint(date_label="2023-10-01", total_sales=total_rev * 0.3, order_count=int(total_orders * 0.3)),
            SalesTrendPoint(date_label="2023-10-02", total_sales=total_rev * 0.7, order_count=int(total_orders * 0.7)),
        ]
    )

async def get_leaderboards(db: AsyncSession, tenant_id: uuid.UUID) -> AnalyticsLeaderboardResponse:
    # Top Customers mock logic
    stmt = select(UniversalCustomer.company_name, func.sum(UniversalTaxInvoice.total_amount), func.count(UniversalTaxInvoice.id))\
        .join(UniversalTaxInvoice, UniversalCustomer.id == UniversalTaxInvoice.customer_id)\
        .where(UniversalTaxInvoice.tenant_id == tenant_id)\
        .group_by(UniversalCustomer.id)\
        .order_by(func.sum(UniversalTaxInvoice.total_amount).desc())\
        .limit(5)
    
    cust_res = await db.execute(stmt)
    top_customers = [AnalyticsLeaderboardItem(name=row[0], value=float(row[1] or 0), count=row[2]) for row in cust_res.fetchall()]

    return AnalyticsLeaderboardResponse(
        top_products=[AnalyticsLeaderboardItem(name="Premium Widget", value=50000.0, count=120)],
        top_customers=top_customers,
        top_channels=[AnalyticsLeaderboardItem(name="Shopify", value=25000.0, count=45)]
    )

async def get_financial_summary(db: AsyncSession, tenant_id: uuid.UUID) -> FinancialSummaryResponse:
    inv_stmt = select(func.sum(UniversalTaxInvoice.total_amount)).where(UniversalTaxInvoice.tenant_id == tenant_id)
    rec_stmt = select(func.sum(UniversalPaymentReceipt.amount_received)).where(UniversalPaymentReceipt.tenant_id == tenant_id)
    
    total_inv = (await db.execute(inv_stmt)).scalar_one_or_none() or 0.0
    total_rec = (await db.execute(rec_stmt)).scalar_one_or_none() or 0.0
    
    return FinancialSummaryResponse(
        total_outstanding=float(total_inv) - float(total_rec),
        total_collected=float(total_rec),
        total_tax_collected=float(total_inv) * 0.18, # Mock 18% assumption
        aging_buckets={
            "0_30": float(total_inv) * 0.4,
            "31_60": float(total_inv) * 0.1,
            "61_plus": 0.0
        }
    )

# -----------------
# Universal Inventory Reports (backs app/api/v1/endpoints/universal_reports.py)
# -----------------

async def get_valuation_summary(db: AsyncSession, tenant_id: uuid.UUID) -> StockValuationSummary:
    agg_stmt = select(
        func.coalesce(func.sum(UniversalStockBalance.quantity_on_hand), 0),
        func.count(func.distinct(UniversalStockBalance.item_id)),
        func.count(func.distinct(UniversalStockBalance.warehouse_id)),
    ).where(UniversalStockBalance.tenant_id == tenant_id)
    total_quantity, item_count, warehouse_count = (await db.execute(agg_stmt)).one()

    # Value items at the average unit cost observed in the ledger (no unit_cost
    # is stored directly on the balance row).
    avg_cost_subq = (
        select(
            UniversalInventoryLedger.item_id.label("item_id"),
            func.avg(UniversalInventoryLedger.unit_cost).label("avg_unit_cost"),
        )
        .where(UniversalInventoryLedger.tenant_id == tenant_id, UniversalInventoryLedger.unit_cost > 0)
        .group_by(UniversalInventoryLedger.item_id)
        .subquery()
    )
    value_stmt = (
        select(func.coalesce(func.sum(UniversalStockBalance.quantity_on_hand * avg_cost_subq.c.avg_unit_cost), 0))
        .select_from(UniversalStockBalance)
        .join(avg_cost_subq, avg_cost_subq.c.item_id == UniversalStockBalance.item_id)
        .where(UniversalStockBalance.tenant_id == tenant_id)
    )
    total_value = (await db.execute(value_stmt)).scalar_one()

    return StockValuationSummary(
        total_quantity=float(total_quantity or 0),
        total_value=float(total_value or 0),
        warehouse_count=warehouse_count or 0,
        item_count=item_count or 0,
    )

async def get_aging_report(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    stmt = select(UniversalStockBalance).where(
        UniversalStockBalance.tenant_id == tenant_id,
        UniversalStockBalance.quantity_on_hand > 0,
    )
    balances = (await db.execute(stmt)).scalars().all()

    now = datetime.now(timezone.utc)
    rows = []
    for b in balances:
        last = b.last_transaction_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days = (now - last).days
        if days <= 30:
            bucket = "0-30"
        elif days <= 90:
            bucket = "31-90"
        elif days <= 180:
            bucket = "91-180"
        else:
            bucket = "180+"
        rows.append({
            "item_id": b.item_id,
            "warehouse_id": b.warehouse_id,
            "quantity_on_hand": float(b.quantity_on_hand),
            "days_since_last_movement": days,
            "aging_bucket": bucket,
        })
    return rows

async def get_abc_analysis(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    """Classic 80/15/5 cumulative-value ABC classification based on
    consumption (outbound movement) value recorded in the ledger."""
    stmt = (
        select(
            UniversalInventoryLedger.item_id,
            UniversalItemMaster.item_code,
            UniversalItemMaster.name,
            func.sum(UniversalInventoryLedger.total_cost).label("consumed_value"),
        )
        .join(UniversalItemMaster, UniversalItemMaster.id == UniversalInventoryLedger.item_id)
        .where(
            UniversalInventoryLedger.tenant_id == tenant_id,
            UniversalInventoryLedger.movement_quantity < 0,
        )
        .group_by(UniversalInventoryLedger.item_id, UniversalItemMaster.item_code, UniversalItemMaster.name)
        .order_by(func.sum(UniversalInventoryLedger.total_cost).desc())
    )
    rows = (await db.execute(stmt)).all()
    total = sum(float(r.consumed_value or 0) for r in rows)

    results = []
    cumulative = 0.0
    for r in rows:
        value = float(r.consumed_value or 0)
        cumulative += value
        cumulative_pct = (cumulative / total * 100) if total > 0 else 0.0
        if cumulative_pct <= 80:
            classification = "A"
        elif cumulative_pct <= 95:
            classification = "B"
        else:
            classification = "C"
        results.append({
            "item_id": r.item_id,
            "item_code": r.item_code,
            "item_name": r.name,
            "total_value_consumed": value,
            "cumulative_percentage": round(cumulative_pct, 2),
            "classification": classification,
        })
    return results
