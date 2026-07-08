import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_invoices import UniversalTaxInvoice
from app.models.universal_customers import UniversalCustomer
from app.models.universal_payments import UniversalPaymentReceipt
from app.schemas.universal_analytics import (
    SalesSummaryResponse, SalesTrendPoint, 
    AnalyticsLeaderboardResponse, AnalyticsLeaderboardItem,
    FinancialSummaryResponse
)

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
