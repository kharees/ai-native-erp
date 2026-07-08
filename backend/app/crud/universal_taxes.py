import uuid
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_taxes import UniversalTaxConfiguration, UniversalHSNSAC
from app.schemas.universal_taxes import (
    UniversalTaxConfigurationCreate, UniversalTaxConfigurationUpdate,
    UniversalHSNSACCreate, UniversalHSNSACUpdate
)

async def create_tax_config(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalTaxConfigurationCreate) -> UniversalTaxConfiguration:
    obj = UniversalTaxConfiguration(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def list_tax_configs(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalTaxConfiguration).where(UniversalTaxConfiguration.tenant_id == tenant_id).order_by(UniversalTaxConfiguration.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalTaxConfiguration.id)).where(UniversalTaxConfiguration.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def create_hsn_sac(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalHSNSACCreate) -> UniversalHSNSAC:
    obj = UniversalHSNSAC(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def list_hsn_sac(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalHSNSAC).where(UniversalHSNSAC.tenant_id == tenant_id).order_by(UniversalHSNSAC.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalHSNSAC.id)).where(UniversalHSNSAC.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()
