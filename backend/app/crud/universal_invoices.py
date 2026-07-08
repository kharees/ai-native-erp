import uuid
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
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
        
    await db.commit()
    await db.refresh(obj)
    return obj

async def list_proforma_invoices(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalProformaInvoice).where(UniversalProformaInvoice.tenant_id == tenant_id).order_by(UniversalProformaInvoice.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalProformaInvoice.id)).where(UniversalProformaInvoice.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def get_proforma_invoice(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalProformaInvoice | None:
    return (await db.execute(select(UniversalProformaInvoice).where(UniversalProformaInvoice.id == id, UniversalProformaInvoice.tenant_id == tenant_id))).scalar_one_or_none()

async def create_tax_invoice(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalTaxInvoiceCreate) -> UniversalTaxInvoice:
    dump = payload.model_dump()
    items_data = dump.pop("items", [])
    
    obj = UniversalTaxInvoice(tenant_id=tenant_id, **dump)
    db.add(obj)
    await db.flush()
    
    for item in items_data:
        db.add(UniversalTaxInvoiceItem(tenant_id=tenant_id, invoice_id=obj.id, **item))
        
    await db.commit()
    await db.refresh(obj)
    return obj

async def list_tax_invoices(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id).order_by(UniversalTaxInvoice.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalTaxInvoice.id)).where(UniversalTaxInvoice.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def get_tax_invoice(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalTaxInvoice | None:
    return (await db.execute(select(UniversalTaxInvoice).where(UniversalTaxInvoice.id == id, UniversalTaxInvoice.tenant_id == tenant_id))).scalar_one_or_none()
