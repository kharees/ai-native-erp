import uuid
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_omnichannel import UniversalChannelConfiguration, UniversalOrderChannelMapping
from app.schemas.universal_omnichannel import (
    UniversalChannelConfigurationCreate, UniversalOrderChannelMappingCreate
)

async def create_channel_config(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalChannelConfigurationCreate) -> UniversalChannelConfiguration:
    obj = UniversalChannelConfiguration(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_channel_configs(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalChannelConfiguration).where(UniversalChannelConfiguration.tenant_id == tenant_id).order_by(UniversalChannelConfiguration.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalChannelConfiguration.id)).where(UniversalChannelConfiguration.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def create_order_mapping(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalOrderChannelMappingCreate) -> UniversalOrderChannelMapping:
    obj = UniversalOrderChannelMapping(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_order_mappings(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalOrderChannelMapping).where(UniversalOrderChannelMapping.tenant_id == tenant_id).order_by(UniversalOrderChannelMapping.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalOrderChannelMapping.id)).where(UniversalOrderChannelMapping.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()
