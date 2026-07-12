import uuid
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_pos import UniversalPOSSession, UniversalPOSHoldBill
from app.schemas.universal_pos import (
    UniversalPOSSessionCreate, UniversalPOSSessionUpdate,
    UniversalPOSHoldBillCreate, UniversalPOSHoldBillUpdate
)

async def create_pos_session(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalPOSSessionCreate) -> UniversalPOSSession:
    obj = UniversalPOSSession(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_pos_sessions(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalPOSSession).where(UniversalPOSSession.tenant_id == tenant_id).order_by(UniversalPOSSession.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalPOSSession.id)).where(UniversalPOSSession.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def create_hold_bill(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalPOSHoldBillCreate) -> UniversalPOSHoldBill:
    obj = UniversalPOSHoldBill(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_hold_bills(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalPOSHoldBill).where(UniversalPOSHoldBill.tenant_id == tenant_id).order_by(UniversalPOSHoldBill.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalPOSHoldBill.id)).where(UniversalPOSHoldBill.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()
