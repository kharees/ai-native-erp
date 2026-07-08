import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_documents as crud
from app.schemas import universal_documents as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

def _not_found(entity: str, id: uuid.UUID) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} '{id}' not found.")

@router.post("/delivery-challans", response_model=schemas.UniversalDeliveryChallanResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Documents", "Create"))])
async def create_delivery_challan(payload: schemas.UniversalDeliveryChallanCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_delivery_challan(db, tenant_id, payload)

@router.get("/delivery-challans", response_model=schemas.PaginatedResponse[schemas.UniversalDeliveryChallanResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Documents", "Read"))])
async def list_delivery_challans(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_delivery_challans(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.post("/packing-slips", response_model=schemas.UniversalPackingSlipResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Documents", "Create"))])
async def create_packing_slip(payload: schemas.UniversalPackingSlipCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_packing_slip(db, tenant_id, payload)

@router.get("/packing-slips", response_model=schemas.PaginatedResponse[schemas.UniversalPackingSlipResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Documents", "Read"))])
async def list_packing_slips(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_packing_slips(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
