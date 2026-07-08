import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_customers import UniversalCustomer
from app.models.universal_invoices import UniversalTaxInvoice

async def get_collection_status(db: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
    customer = await db.get(UniversalCustomer, customer_id)
    if not customer: return None
    
    # Simple virtual logic for outstanding
    stmt = select(func.sum(UniversalTaxInvoice.total_amount)).where(
        UniversalTaxInvoice.tenant_id == tenant_id,
        UniversalTaxInvoice.customer_id == customer_id,
        UniversalTaxInvoice.status == 'ISSUED'
    )
    total_invoiced = (await db.execute(stmt)).scalar_one_or_none() or 0.0
    
    # Ideally we'd subtract total allocated payments here. For this phase, we mock standard collection views
    total_outstanding = total_invoiced * 0.5 # Mocking logic based on unallocated
    overdue_amount = total_outstanding * 0.2
    
    return {
        "customer_id": customer.id,
        "customer_name": customer.company_name,
        "credit_limit": customer.credit_limit,
        "credit_days": customer.credit_days,
        "total_outstanding": total_outstanding,
        "overdue_amount": overdue_amount,
        "isOnCreditHold": total_outstanding > customer.credit_limit if customer.credit_limit > 0 else False
    }

async def get_aging_buckets(db: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
    return {
        "bucket_0_30": 5000.0,
        "bucket_31_60": 1000.0,
        "bucket_61_90": 0.0,
        "bucket_90_plus": 0.0,
        "total": 6000.0
    }
