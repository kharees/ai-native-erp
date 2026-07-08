import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_ledger import UniversalInventoryLedger

async def list_ledger_entries(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
    item_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    bin_id: uuid.UUID | None = None,
    reference_type: str | None = None
):
    stmt = select(UniversalInventoryLedger).where(UniversalInventoryLedger.tenant_id == tenant_id)
    
    if item_id:
        stmt = stmt.where(UniversalInventoryLedger.item_id == item_id)
    if warehouse_id:
        stmt = stmt.where(UniversalInventoryLedger.warehouse_id == warehouse_id)
    if bin_id:
        stmt = stmt.where(UniversalInventoryLedger.bin_id == bin_id)
    if reference_type:
        stmt = stmt.where(UniversalInventoryLedger.reference_type == reference_type)
        
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(UniversalInventoryLedger.created_at.desc()).limit(limit).offset(offset)
    items = (await db.execute(stmt)).scalars().all()
    
    return items, total
