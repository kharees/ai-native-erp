import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_shipping as crud
from app.schemas import universal_shipping as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.post("/couriers", response_model=schemas.UniversalShippingCourierResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Shipping", "Create"))])
async def create_shipping_courier(payload: schemas.UniversalShippingCourierCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_shipping_courier(db, tenant_id, payload)

@router.get("/couriers", response_model=schemas.PaginatedResponse[schemas.UniversalShippingCourierResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Shipping", "Read"))])
async def list_shipping_couriers(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_shipping_couriers(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.post("/dispatches", response_model=schemas.UniversalOrderDispatchResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Shipping", "Create"))])
async def create_order_dispatch(payload: schemas.UniversalOrderDispatchCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_order_dispatch(db, tenant_id, payload)

@router.get("/dispatches", response_model=schemas.PaginatedResponse[schemas.UniversalOrderDispatchResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Shipping", "Read"))])
async def list_order_dispatches(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_order_dispatches(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
