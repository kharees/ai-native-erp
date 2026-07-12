import uuid
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_documents import (
    UniversalDeliveryChallan, UniversalDeliveryChallanItem,
    UniversalPackingSlip, UniversalPackingSlipItem
)
from app.schemas.universal_documents import (
    UniversalDeliveryChallanCreate, UniversalDeliveryChallanUpdate,
    UniversalPackingSlipCreate, UniversalPackingSlipUpdate
)

async def create_delivery_challan(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalDeliveryChallanCreate) -> UniversalDeliveryChallan:
    dump = payload.model_dump()
    items_data = dump.pop("items", [])
    
    obj = UniversalDeliveryChallan(tenant_id=tenant_id, **dump)
    db.add(obj)
    await db.flush()
    
    for item in items_data:
        db.add(UniversalDeliveryChallanItem(tenant_id=tenant_id, challan_id=obj.id, **item))
        
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_delivery_challans(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalDeliveryChallan).where(UniversalDeliveryChallan.tenant_id == tenant_id).order_by(UniversalDeliveryChallan.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalDeliveryChallan.id)).where(UniversalDeliveryChallan.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def create_packing_slip(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalPackingSlipCreate) -> UniversalPackingSlip:
    dump = payload.model_dump()
    items_data = dump.pop("items", [])
    
    obj = UniversalPackingSlip(tenant_id=tenant_id, **dump)
    db.add(obj)
    await db.flush()
    
    for item in items_data:
        db.add(UniversalPackingSlipItem(tenant_id=tenant_id, slip_id=obj.id, **item))
        
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_packing_slips(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalPackingSlip).where(UniversalPackingSlip.tenant_id == tenant_id).order_by(UniversalPackingSlip.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalPackingSlip.id)).where(UniversalPackingSlip.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()
