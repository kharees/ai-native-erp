import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_taxes as crud
from app.schemas import universal_taxes as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.post("/configurations", response_model=schemas.UniversalTaxConfigurationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Taxes", "Create"))])
async def create_tax_config(payload: schemas.UniversalTaxConfigurationCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_tax_config(db, tenant_id, payload)

@router.get("/configurations", response_model=schemas.PaginatedResponse[schemas.UniversalTaxConfigurationResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Taxes", "Read"))])
async def list_tax_configs(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_tax_configs(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.post("/hsn-sac", response_model=schemas.UniversalHSNSACResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Taxes", "Create"))])
async def create_hsn_sac(payload: schemas.UniversalHSNSACCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_hsn_sac(db, tenant_id, payload)

@router.get("/hsn-sac", response_model=schemas.PaginatedResponse[schemas.UniversalHSNSACResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Taxes", "Read"))])
async def list_hsn_sac(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_hsn_sac(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
