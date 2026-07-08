import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_pos as crud
from app.schemas import universal_pos as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.post("/sessions", response_model=schemas.UniversalPOSSessionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "POS", "Create"))])
async def create_pos_session(payload: schemas.UniversalPOSSessionCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_pos_session(db, tenant_id, payload)

@router.get("/sessions", response_model=schemas.PaginatedResponse[schemas.UniversalPOSSessionResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "POS", "Read"))])
async def list_pos_sessions(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_pos_sessions(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.post("/hold-bills", response_model=schemas.UniversalPOSHoldBillResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "POS", "Create"))])
async def create_hold_bill(payload: schemas.UniversalPOSHoldBillCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_hold_bill(db, tenant_id, payload)

@router.get("/hold-bills", response_model=schemas.PaginatedResponse[schemas.UniversalPOSHoldBillResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "POS", "Read"))])
async def list_hold_bills(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_hold_bills(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
