import uuid
from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.crud import universal_tracking as crud
from app.schemas import universal_tracking as schemas
from app.schemas.universal_inventory import PaginatedResponse
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

# -----------------
# Batches
# -----------------
@router.post("/batches", response_model=schemas.UniversalBatchMasterResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalInventory", "Tracking", "Create"))])
async def create_batch(payload: schemas.UniversalBatchMasterCreate, tenant_id: TenantIDDep, db: DBDep):
    try:
        return await crud.create_batch(db, tenant_id, payload)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Batch number already exists for this item.")

@router.get("/batches", response_model=PaginatedResponse[schemas.UniversalBatchMasterResponse], dependencies=[Depends(RequirePermission("UniversalInventory", "Tracking", "Read"))])
async def list_batches(
    tenant_id: TenantIDDep, 
    db: DBDep, 
    limit: int = 20, 
    offset: int = 0,
    item_id: uuid.UUID | None = None,
    batch_number: str | None = None,
    status: str | None = None
):
    items, total = await crud.list_batches(db, tenant_id, limit, offset, item_id, batch_number, status)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/expiry-alerts", response_model=list[schemas.UniversalBatchMasterResponse], dependencies=[Depends(RequirePermission("UniversalInventory", "Tracking", "Read"))])
async def get_expiry_alerts(cutoff_date: date, tenant_id: TenantIDDep, db: DBDep):
    return await crud.get_near_expiry_batches(db, tenant_id, cutoff_date)

# -----------------
# Serials
# -----------------
@router.get("/serials", response_model=PaginatedResponse[schemas.UniversalSerialMasterResponse], dependencies=[Depends(RequirePermission("UniversalInventory", "Tracking", "Read"))])
async def list_serials(
    tenant_id: TenantIDDep, 
    db: DBDep, 
    limit: int = 20, 
    offset: int = 0,
    item_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
    serial_number: str | None = None,
    status: str | None = None
):
    items, total = await crud.list_serials(db, tenant_id, limit, offset, item_id, batch_id, serial_number, status)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
