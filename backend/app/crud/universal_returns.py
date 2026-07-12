import uuid
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_returns import (
    UniversalCreditNote, UniversalCreditNoteItem,
    UniversalDebitNote, UniversalDebitNoteItem,
    UniversalSalesReturn, UniversalSalesReturnItem
)
from app.schemas.universal_returns import (
    UniversalCreditNoteCreate, UniversalCreditNoteUpdate,
    UniversalDebitNoteCreate, UniversalDebitNoteUpdate,
    UniversalSalesReturnCreate, UniversalSalesReturnUpdate
)

async def create_credit_note(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalCreditNoteCreate) -> UniversalCreditNote:
    dump = payload.model_dump()
    items_data = dump.pop("items", [])
    
    obj = UniversalCreditNote(tenant_id=tenant_id, **dump)
    db.add(obj)
    await db.flush()
    
    for item in items_data:
        db.add(UniversalCreditNoteItem(tenant_id=tenant_id, note_id=obj.id, **item))
        
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_credit_notes(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalCreditNote).where(UniversalCreditNote.tenant_id == tenant_id).order_by(UniversalCreditNote.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalCreditNote.id)).where(UniversalCreditNote.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def create_debit_note(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalDebitNoteCreate) -> UniversalDebitNote:
    dump = payload.model_dump()
    items_data = dump.pop("items", [])
    
    obj = UniversalDebitNote(tenant_id=tenant_id, **dump)
    db.add(obj)
    await db.flush()
    
    for item in items_data:
        db.add(UniversalDebitNoteItem(tenant_id=tenant_id, note_id=obj.id, **item))
        
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_debit_notes(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalDebitNote).where(UniversalDebitNote.tenant_id == tenant_id).order_by(UniversalDebitNote.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalDebitNote.id)).where(UniversalDebitNote.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def create_sales_return(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalSalesReturnCreate) -> UniversalSalesReturn:
    dump = payload.model_dump()
    items_data = dump.pop("items", [])
    
    obj = UniversalSalesReturn(tenant_id=tenant_id, **dump)
    db.add(obj)
    await db.flush()
    
    for item in items_data:
        db.add(UniversalSalesReturnItem(tenant_id=tenant_id, return_id=obj.id, **item))
        
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_sales_returns(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalSalesReturn).where(UniversalSalesReturn.tenant_id == tenant_id).order_by(UniversalSalesReturn.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalSalesReturn.id)).where(UniversalSalesReturn.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()
