import uuid
from datetime import date
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_tracking import UniversalBatchMaster, UniversalSerialMaster, UniversalBatchStock
from app.schemas.universal_tracking import UniversalBatchMasterCreate, UniversalSerialMasterCreate

# -----------------
# Batches
# -----------------
async def create_batch(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalBatchMasterCreate) -> UniversalBatchMaster:
    obj = UniversalBatchMaster(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def list_batches(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
    item_id: uuid.UUID | None = None,
    batch_number: str | None = None,
    status: str | None = None
):
    stmt = select(UniversalBatchMaster).where(UniversalBatchMaster.tenant_id == tenant_id)
    
    if item_id: stmt = stmt.where(UniversalBatchMaster.item_id == item_id)
    if batch_number: stmt = stmt.where(UniversalBatchMaster.batch_number.like(f"%{batch_number}%"))
    if status: stmt = stmt.where(UniversalBatchMaster.status == status)
        
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(UniversalBatchMaster.created_at.desc()).limit(limit).offset(offset)
    items = (await db.execute(stmt)).scalars().all()
    
    return items, total

async def get_near_expiry_batches(db: AsyncSession, tenant_id: uuid.UUID, cutoff_date: date):
    # Get active batches expiring before cutoff_date
    stmt = select(UniversalBatchMaster).where(
        UniversalBatchMaster.tenant_id == tenant_id,
        UniversalBatchMaster.status == 'active',
        UniversalBatchMaster.expiry_date != None,
        UniversalBatchMaster.expiry_date <= cutoff_date
    ).order_by(UniversalBatchMaster.expiry_date.asc())
    
    items = (await db.execute(stmt)).scalars().all()
    return items

# -----------------
# Serials
# -----------------
async def list_serials(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
    item_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
    serial_number: str | None = None,
    status: str | None = None
):
    stmt = select(UniversalSerialMaster).where(UniversalSerialMaster.tenant_id == tenant_id)
    
    if item_id: stmt = stmt.where(UniversalSerialMaster.item_id == item_id)
    if batch_id: stmt = stmt.where(UniversalSerialMaster.batch_id == batch_id)
    if serial_number: stmt = stmt.where(UniversalSerialMaster.serial_number.like(f"%{serial_number}%"))
    if status: stmt = stmt.where(UniversalSerialMaster.status == status)
        
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(UniversalSerialMaster.created_at.desc()).limit(limit).offset(offset)
    items = (await db.execute(stmt)).scalars().all()
    
    return items, total
