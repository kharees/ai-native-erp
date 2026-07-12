import uuid
from sqlalchemy import select, func, update, exc
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import paginate
from app.models.universal_inventory import (
    UniversalCategory,
    UniversalBrand,
    UniversalUOM,
    UniversalItemMaster
)
from app.schemas.universal_inventory import (
    UniversalCategoryCreate, UniversalCategoryUpdate,
    UniversalBrandCreate, UniversalBrandUpdate,
    UniversalUOMCreate, UniversalUOMUpdate,
    UniversalItemMasterCreate, UniversalItemMasterUpdate
)

# Helpers
async def get_paginated(
    db: AsyncSession, model, tenant_id: uuid.UUID, limit: int, offset: int
):
    count_stmt = select(func.count(model.id)).where(model.tenant_id == tenant_id, model.is_active == True)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = select(model).where(model.tenant_id == tenant_id, model.is_active == True).order_by(model.created_at.desc()).limit(limit).offset(offset)
    items = (await db.execute(stmt)).scalars().all()
    
    return items, total

# Category CRUD
async def create_category(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalCategoryCreate) -> UniversalCategory:
    obj = UniversalCategory(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_category(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalCategory | None:
    stmt = select(UniversalCategory).where(UniversalCategory.id == id, UniversalCategory.tenant_id == tenant_id, UniversalCategory.is_active == True)
    return (await db.execute(stmt)).scalar_one_or_none()

async def list_categories(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    return await get_paginated(db, UniversalCategory, tenant_id, limit, offset)

async def update_category(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID, payload: UniversalCategoryUpdate) -> UniversalCategory | None:
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return await get_category(db, tenant_id, id)
    stmt = update(UniversalCategory).where(UniversalCategory.id == id, UniversalCategory.tenant_id == tenant_id).values(**update_data).returning(UniversalCategory)
    res = (await db.execute(stmt)).scalar_one_or_none()
    await db.commit()
    return res

async def delete_category(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> bool:
    stmt = update(UniversalCategory).where(UniversalCategory.id == id, UniversalCategory.tenant_id == tenant_id).values(is_active=False)
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount > 0

# Brand CRUD
async def create_brand(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalBrandCreate) -> UniversalBrand:
    obj = UniversalBrand(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_brand(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalBrand | None:
    stmt = select(UniversalBrand).where(UniversalBrand.id == id, UniversalBrand.tenant_id == tenant_id, UniversalBrand.is_active == True)
    return (await db.execute(stmt)).scalar_one_or_none()

async def list_brands(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    return await get_paginated(db, UniversalBrand, tenant_id, limit, offset)

async def update_brand(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID, payload: UniversalBrandUpdate) -> UniversalBrand | None:
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return await get_brand(db, tenant_id, id)
    stmt = update(UniversalBrand).where(UniversalBrand.id == id, UniversalBrand.tenant_id == tenant_id).values(**update_data).returning(UniversalBrand)
    res = (await db.execute(stmt)).scalar_one_or_none()
    await db.commit()
    return res

async def delete_brand(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> bool:
    stmt = update(UniversalBrand).where(UniversalBrand.id == id, UniversalBrand.tenant_id == tenant_id).values(is_active=False)
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount > 0

# UOM CRUD
async def create_uom(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalUOMCreate) -> UniversalUOM:
    obj = UniversalUOM(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_uom(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalUOM | None:
    stmt = select(UniversalUOM).where(UniversalUOM.id == id, UniversalUOM.tenant_id == tenant_id, UniversalUOM.is_active == True)
    return (await db.execute(stmt)).scalar_one_or_none()

async def list_uoms(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    return await get_paginated(db, UniversalUOM, tenant_id, limit, offset)

async def update_uom(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID, payload: UniversalUOMUpdate) -> UniversalUOM | None:
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return await get_uom(db, tenant_id, id)
    stmt = update(UniversalUOM).where(UniversalUOM.id == id, UniversalUOM.tenant_id == tenant_id).values(**update_data).returning(UniversalUOM)
    res = (await db.execute(stmt)).scalar_one_or_none()
    await db.commit()
    return res

async def delete_uom(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> bool:
    stmt = update(UniversalUOM).where(UniversalUOM.id == id, UniversalUOM.tenant_id == tenant_id).values(is_active=False)
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount > 0

# Item Master CRUD
async def create_item(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None, payload: UniversalItemMasterCreate) -> UniversalItemMaster:
    obj = UniversalItemMaster(
        tenant_id=tenant_id,
        created_by=user_id,
        **payload.model_dump()
    )
    db.add(obj)
    try:
        await db.commit()
    except exc.IntegrityError:
        await db.rollback()
        raise
    await db.refresh(obj)
    return obj

async def get_item(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalItemMaster | None:
    stmt = select(UniversalItemMaster).where(UniversalItemMaster.id == id, UniversalItemMaster.tenant_id == tenant_id, UniversalItemMaster.is_active == True)
    return (await db.execute(stmt)).scalar_one_or_none()

async def list_items(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
    category_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None
):
    stmt = select(UniversalItemMaster).where(
        UniversalItemMaster.tenant_id == tenant_id,
        UniversalItemMaster.is_active == True
    )

    if category_id:
        stmt = stmt.where(UniversalItemMaster.category_id == category_id)
    if status:
        stmt = stmt.where(UniversalItemMaster.status == status)
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (func.lower(UniversalItemMaster.name).like(search_pattern.lower())) |
            (func.lower(UniversalItemMaster.sku).like(search_pattern.lower())) |
            (func.lower(UniversalItemMaster.item_code).like(search_pattern.lower()))
        )

    return await paginate(db, stmt, UniversalItemMaster.created_at.desc(), limit, offset)

async def update_item(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None, id: uuid.UUID, payload: UniversalItemMasterUpdate) -> UniversalItemMaster | None:
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return await get_item(db, tenant_id, id)
    
    update_data["updated_by"] = user_id
    stmt = update(UniversalItemMaster).where(UniversalItemMaster.id == id, UniversalItemMaster.tenant_id == tenant_id).values(**update_data).returning(UniversalItemMaster)
    
    try:
        res = (await db.execute(stmt)).scalar_one_or_none()
        await db.commit()
    except exc.IntegrityError:
        await db.rollback()
        raise
    return res

async def delete_item(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> bool:
    stmt = update(UniversalItemMaster).where(UniversalItemMaster.id == id, UniversalItemMaster.tenant_id == tenant_id).values(is_active=False)
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount > 0
