import uuid
from fastapi import HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_customers import UniversalCustomer
from app.models.universal_invoices import (
    UniversalProformaInvoice, UniversalProformaInvoiceItem,
    UniversalTaxInvoice, UniversalTaxInvoiceItem
)
from app.schemas.universal_invoices import (
    UniversalProformaInvoiceCreate, UniversalProformaInvoiceUpdate,
    UniversalTaxInvoiceCreate, UniversalTaxInvoiceUpdate
)

async def create_proforma_invoice(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalProformaInvoiceCreate) -> UniversalProformaInvoice:
    dump = payload.model_dump()
    items_data = dump.pop("items", [])
    
    obj = UniversalProformaInvoice(tenant_id=tenant_id, **dump)
    db.add(obj)
    await db.flush()
    
    for item in items_data:
        db.add(UniversalProformaInvoiceItem(tenant_id=tenant_id, pi_id=obj.id, **item))
        
    await db.flush()
    await db.refresh(obj)
    await db.refresh(obj, ["items"])
    return obj

async def list_proforma_invoices(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = (
        select(UniversalProformaInvoice)
        .options(selectinload(UniversalProformaInvoice.items))
        .where(UniversalProformaInvoice.tenant_id == tenant_id)
        .order_by(UniversalProformaInvoice.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    count_stmt = select(func.count(UniversalProformaInvoice.id)).where(UniversalProformaInvoice.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def get_proforma_invoice(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalProformaInvoice | None:
    stmt = (
        select(UniversalProformaInvoice)
        .options(selectinload(UniversalProformaInvoice.items))
        .where(UniversalProformaInvoice.id == id, UniversalProformaInvoice.tenant_id == tenant_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()

async def create_tax_invoice(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalTaxInvoiceCreate) -> UniversalTaxInvoice:
    dump = payload.model_dump()
    items_data = dump.pop("items", [])

    # customer_id was previously trusted with no ownership check, so an
    # invoice could reference another tenant's customer — that reference
    # then surfaces cross-tenant in join-based queries elsewhere (e.g.
    # universal_analytics.py's leaderboards) that assume a tenant-scoped
    # invoice's customer already belongs to the same tenant (Sprint 5 #3
    # verification finding, LOW-MEDIUM). Validated before any write.
    customer_stmt = select(UniversalCustomer.id).where(
        UniversalCustomer.id == dump["customer_id"], UniversalCustomer.tenant_id == tenant_id
    )
    if (await db.execute(customer_stmt)).scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    # invoice_number is optional on the schema because
    # create_invoice_with_stock_deduction (app/services/sales_fulfillment.py)
    # always generates it server-side and never reaches this function with
    # one pre-filled. This direct-create path has no numbering of its own,
    # so it still requires the caller to supply one.
    if not dump.get("invoice_number"):
        raise HTTPException(status_code=400, detail="invoice_number is required.")

    obj = UniversalTaxInvoice(tenant_id=tenant_id, **dump)
    db.add(obj)
    await db.flush()
    
    for item in items_data:
        db.add(UniversalTaxInvoiceItem(tenant_id=tenant_id, invoice_id=obj.id, **item))
        
    await db.flush()
    await db.refresh(obj)
    await db.refresh(obj, ["items"])
    return obj

async def list_tax_invoices(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = (
        select(UniversalTaxInvoice)
        .options(selectinload(UniversalTaxInvoice.items))
        .where(UniversalTaxInvoice.tenant_id == tenant_id)
        .order_by(UniversalTaxInvoice.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    count_stmt = select(func.count(UniversalTaxInvoice.id)).where(UniversalTaxInvoice.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def get_tax_invoice(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalTaxInvoice | None:
    stmt = (
        select(UniversalTaxInvoice)
        .options(selectinload(UniversalTaxInvoice.items))
        .where(UniversalTaxInvoice.id == id, UniversalTaxInvoice.tenant_id == tenant_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()
