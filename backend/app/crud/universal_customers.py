import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import paginate
from app.models.universal_customers import (
    UniversalCustomerGroup, UniversalCustomerType, UniversalCustomerCategory, UniversalCustomer,
    UniversalCustomerContact, UniversalCustomerAddress
)
from app.schemas.universal_customers import (
    UniversalCustomerGroupCreate, UniversalCustomerGroupUpdate,
    UniversalCustomerTypeCreate, UniversalCustomerTypeUpdate,
    UniversalCustomerCategoryCreate, UniversalCustomerCategoryUpdate,
    UniversalCustomerCreate, UniversalCustomerUpdate,
    UniversalCustomerContactCreate, UniversalCustomerContactUpdate,
    UniversalCustomerAddressCreate, UniversalCustomerAddressUpdate
)

async def get_paginated(db: AsyncSession, model, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(model).where(model.tenant_id == tenant_id)
    return await paginate(db, stmt, model.created_at.desc(), limit, offset)

# Groups
async def create_group(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalCustomerGroupCreate) -> UniversalCustomerGroup:
    obj = UniversalCustomerGroup(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def get_group(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalCustomerGroup | None:
    return (await db.execute(select(UniversalCustomerGroup).where(UniversalCustomerGroup.id == id, UniversalCustomerGroup.tenant_id == tenant_id))).scalar_one_or_none()

async def update_group(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID, payload: UniversalCustomerGroupUpdate) -> UniversalCustomerGroup | None:
    obj = await get_group(db, tenant_id, id)
    if not obj: return None
    for k, v in payload.model_dump(exclude_unset=True).items(): setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

# Customers
async def create_customer(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalCustomerCreate) -> UniversalCustomer:
    obj = UniversalCustomer(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_customers(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int, search: str | None = None):
    stmt = select(UniversalCustomer).where(UniversalCustomer.tenant_id == tenant_id)
    if search:
        stmt = stmt.where(UniversalCustomer.name.ilike(f"%{search}%"))
    return await paginate(db, stmt, UniversalCustomer.created_at.desc(), limit, offset)

async def get_customer(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalCustomer | None:
    return (await db.execute(select(UniversalCustomer).where(UniversalCustomer.id == id, UniversalCustomer.tenant_id == tenant_id))).scalar_one_or_none()

async def update_customer(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID, payload: UniversalCustomerUpdate) -> UniversalCustomer | None:
    obj = await get_customer(db, tenant_id, id)
    if not obj: return None
    for k, v in payload.model_dump(exclude_unset=True).items(): setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_customer(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> bool:
    obj = await get_customer(db, tenant_id, id)
    if not obj: return False
    await db.delete(obj)
    await db.flush()
    return True
