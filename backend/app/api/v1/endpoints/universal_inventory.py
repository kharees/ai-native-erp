import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.crud import universal_inventory as crud
from app.schemas import universal_inventory as schemas
from app.middleware.tenant_auth import TenantIDDep, UserIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

def _not_found(entity: str, id: uuid.UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} '{id}' not found."
    )

def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

# -----------------
# Categories
# -----------------
@router.post("/categories", response_model=schemas.UniversalCategoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalInventory", "Categories", "Create"))])
async def create_category(payload: schemas.UniversalCategoryCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_category(db, tenant_id, payload)

@router.get("/categories", response_model=schemas.PaginatedResponse[schemas.UniversalCategoryResponse], dependencies=[Depends(RequirePermission("UniversalInventory", "Categories", "Read"))])
async def list_categories(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_categories(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/categories/{id}", response_model=schemas.UniversalCategoryResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "Categories", "Read"))])
async def get_category(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_category(db, tenant_id, id)
    if not obj: raise _not_found("Category", id)
    return obj

@router.patch("/categories/{id}", response_model=schemas.UniversalCategoryResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "Categories", "Update"))])
async def update_category(id: uuid.UUID, payload: schemas.UniversalCategoryUpdate, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.update_category(db, tenant_id, id, payload)
    if not obj: raise _not_found("Category", id)
    return obj

@router.delete("/categories/{id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, dependencies=[Depends(RequirePermission("UniversalInventory", "Categories", "Delete"))])
async def delete_category(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    if not await crud.delete_category(db, tenant_id, id): raise _not_found("Category", id)

# -----------------
# Brands
# -----------------
@router.post("/brands", response_model=schemas.UniversalBrandResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalInventory", "Brands", "Create"))])
async def create_brand(payload: schemas.UniversalBrandCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_brand(db, tenant_id, payload)

@router.get("/brands", response_model=schemas.PaginatedResponse[schemas.UniversalBrandResponse], dependencies=[Depends(RequirePermission("UniversalInventory", "Brands", "Read"))])
async def list_brands(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_brands(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/brands/{id}", response_model=schemas.UniversalBrandResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "Brands", "Read"))])
async def get_brand(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_brand(db, tenant_id, id)
    if not obj: raise _not_found("Brand", id)
    return obj

@router.patch("/brands/{id}", response_model=schemas.UniversalBrandResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "Brands", "Update"))])
async def update_brand(id: uuid.UUID, payload: schemas.UniversalBrandUpdate, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.update_brand(db, tenant_id, id, payload)
    if not obj: raise _not_found("Brand", id)
    return obj

@router.delete("/brands/{id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, dependencies=[Depends(RequirePermission("UniversalInventory", "Brands", "Delete"))])
async def delete_brand(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    if not await crud.delete_brand(db, tenant_id, id): raise _not_found("Brand", id)

# -----------------
# UOMs
# -----------------
@router.post("/uoms", response_model=schemas.UniversalUOMResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalInventory", "UOMs", "Create"))])
async def create_uom(payload: schemas.UniversalUOMCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_uom(db, tenant_id, payload)

@router.get("/uoms", response_model=schemas.PaginatedResponse[schemas.UniversalUOMResponse], dependencies=[Depends(RequirePermission("UniversalInventory", "UOMs", "Read"))])
async def list_uoms(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_uoms(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/uoms/{id}", response_model=schemas.UniversalUOMResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "UOMs", "Read"))])
async def get_uom(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_uom(db, tenant_id, id)
    if not obj: raise _not_found("UOM", id)
    return obj

@router.patch("/uoms/{id}", response_model=schemas.UniversalUOMResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "UOMs", "Update"))])
async def update_uom(id: uuid.UUID, payload: schemas.UniversalUOMUpdate, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.update_uom(db, tenant_id, id, payload)
    if not obj: raise _not_found("UOM", id)
    return obj

@router.delete("/uoms/{id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, dependencies=[Depends(RequirePermission("UniversalInventory", "UOMs", "Delete"))])
async def delete_uom(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    if not await crud.delete_uom(db, tenant_id, id): raise _not_found("UOM", id)

# -----------------
# Item Master
# -----------------
@router.post("/items", response_model=schemas.UniversalItemMasterResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalInventory", "Items", "Create"))])
async def create_item(payload: schemas.UniversalItemMasterCreate, tenant_id: TenantIDDep, user_id: UserIDDep, db: DBDep):
    try:
        return await crud.create_item(db, tenant_id, user_id, payload)
    except IntegrityError as exc:
        msg = str(exc)
        if "uq_universal_item_tenant_code" in msg:
            raise _conflict(f"Item Code '{payload.item_code}' already exists.")
        if "uq_universal_item_tenant_sku" in msg:
            raise _conflict(f"SKU '{payload.sku}' already exists.")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Database constraint violated.")

@router.get("/items", response_model=schemas.PaginatedResponse[schemas.UniversalItemMasterResponse], dependencies=[Depends(RequirePermission("UniversalInventory", "Items", "Read"))])
async def list_items(
    tenant_id: TenantIDDep, 
    db: DBDep, 
    limit: int = 20, 
    offset: int = 0,
    category_id: uuid.UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None
):
    items, total = await crud.list_items(db, tenant_id, limit, offset, category_id, status_filter, search)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/items/{id}", response_model=schemas.UniversalItemMasterResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "Items", "Read"))])
async def get_item(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_item(db, tenant_id, id)
    if not obj: raise _not_found("Item", id)
    return obj

@router.patch("/items/{id}", response_model=schemas.UniversalItemMasterResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "Items", "Update"))])
async def update_item(id: uuid.UUID, payload: schemas.UniversalItemMasterUpdate, tenant_id: TenantIDDep, user_id: UserIDDep, db: DBDep):
    try:
        obj = await crud.update_item(db, tenant_id, user_id, id, payload)
        if not obj: raise _not_found("Item", id)
        return obj
    except IntegrityError:
        raise _conflict("Unique constraint violation. Check SKU or Item Code.")

@router.delete("/items/{id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, dependencies=[Depends(RequirePermission("UniversalInventory", "Items", "Delete"))])
async def delete_item(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    if not await crud.delete_item(db, tenant_id, id): raise _not_found("Item", id)
