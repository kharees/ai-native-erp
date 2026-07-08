import uuid
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_shipping import UniversalShippingCourier, UniversalOrderDispatch
from app.schemas.universal_shipping import (
    UniversalShippingCourierCreate, UniversalOrderDispatchCreate
)

async def create_shipping_courier(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalShippingCourierCreate) -> UniversalShippingCourier:
    obj = UniversalShippingCourier(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def list_shipping_couriers(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalShippingCourier).where(UniversalShippingCourier.tenant_id == tenant_id).order_by(UniversalShippingCourier.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalShippingCourier.id)).where(UniversalShippingCourier.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def create_order_dispatch(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalOrderDispatchCreate) -> UniversalOrderDispatch:
    obj = UniversalOrderDispatch(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def list_order_dispatches(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalOrderDispatch).where(UniversalOrderDispatch.tenant_id == tenant_id).order_by(UniversalOrderDispatch.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalOrderDispatch.id)).where(UniversalOrderDispatch.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()
