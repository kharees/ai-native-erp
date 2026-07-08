import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_omnichannel as crud
from app.schemas import universal_omnichannel as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.post("/channels", response_model=schemas.UniversalChannelConfigurationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Omnichannel", "Create"))])
async def create_channel_config(payload: schemas.UniversalChannelConfigurationCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_channel_config(db, tenant_id, payload)

@router.get("/channels", response_model=schemas.PaginatedResponse[schemas.UniversalChannelConfigurationResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Omnichannel", "Read"))])
async def list_channel_configs(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_channel_configs(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.post("/orders", response_model=schemas.UniversalOrderChannelMappingResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Omnichannel", "Create"))])
async def create_order_mapping(payload: schemas.UniversalOrderChannelMappingCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_order_mapping(db, tenant_id, payload)

@router.get("/orders", response_model=schemas.PaginatedResponse[schemas.UniversalOrderChannelMappingResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Omnichannel", "Read"))])
async def list_order_mappings(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_order_mappings(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
