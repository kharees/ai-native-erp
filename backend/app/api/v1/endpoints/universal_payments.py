import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_payments as crud
from app.schemas import universal_payments as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.post("/receipts", response_model=schemas.UniversalPaymentReceiptResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Payments", "Create"))])
async def create_payment_receipt(payload: schemas.UniversalPaymentReceiptCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_payment_receipt(db, tenant_id, payload)

@router.get("/receipts", response_model=schemas.PaginatedResponse[schemas.UniversalPaymentReceiptResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Payments", "Read"))])
async def list_payment_receipts(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_payment_receipts(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.post("/allocations", response_model=schemas.UniversalPaymentAllocationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Payments", "Create"))])
async def create_payment_allocation(payload: schemas.UniversalPaymentAllocationCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_payment_allocation(db, tenant_id, payload)

@router.post("/refunds", response_model=schemas.UniversalRefundResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Payments", "Create"))])
async def create_refund(payload: schemas.UniversalRefundCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_refund(db, tenant_id, payload)

@router.get("/refunds", response_model=schemas.PaginatedResponse[schemas.UniversalRefundResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Payments", "Read"))])
async def list_refunds(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_refunds(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
