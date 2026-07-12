import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import paginate
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
        
    return await paginate(db, stmt, UniversalInventoryLedger.created_at.desc(), limit, offset)
