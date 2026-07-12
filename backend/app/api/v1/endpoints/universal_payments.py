import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_payments as crud
from app.schemas import universal_payments as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission
from app.services.idempotency import claim_idempotency_key, complete_idempotency_key

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]

@router.post("/receipts", response_model=schemas.UniversalPaymentReceiptResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Payments", "Create"))])
async def create_payment_receipt(payload: schemas.UniversalPaymentReceiptCreate, tenant_id: TenantIDDep, db: DBDep, idempotency_key: IdempotencyKeyHeader = None):
    claim = await claim_idempotency_key(db, tenant_id, "payments.receipts", idempotency_key)
    if claim.replay_response is not None:
        return claim.replay_response
    if claim.conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A request with this Idempotency-Key is already being processed.")

    obj = await crud.create_payment_receipt(db, tenant_id, payload)

    if claim.should_complete:
        response_body = jsonable_encoder(schemas.UniversalPaymentReceiptResponse.model_validate(obj))
        await complete_idempotency_key(db, tenant_id, "payments.receipts", idempotency_key, obj.id, response_body)

    return obj

@router.get("/receipts", response_model=schemas.PaginatedResponse[schemas.UniversalPaymentReceiptResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Payments", "Read"))])
async def list_payment_receipts(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_payment_receipts(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.post("/allocations", response_model=schemas.UniversalPaymentAllocationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Payments", "Create"))])
async def create_payment_allocation(payload: schemas.UniversalPaymentAllocationCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_payment_allocation(db, tenant_id, payload)

@router.post("/refunds", response_model=schemas.UniversalRefundResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Payments", "Create"))])
async def create_refund(payload: schemas.UniversalRefundCreate, tenant_id: TenantIDDep, db: DBDep, idempotency_key: IdempotencyKeyHeader = None):
    claim = await claim_idempotency_key(db, tenant_id, "payments.refunds", idempotency_key)
    if claim.replay_response is not None:
        return claim.replay_response
    if claim.conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A request with this Idempotency-Key is already being processed.")

    obj = await crud.create_refund(db, tenant_id, payload)

    if claim.should_complete:
        response_body = jsonable_encoder(schemas.UniversalRefundResponse.model_validate(obj))
        await complete_idempotency_key(db, tenant_id, "payments.refunds", idempotency_key, obj.id, response_body)

    return obj

@router.get("/refunds", response_model=schemas.PaginatedResponse[schemas.UniversalRefundResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Payments", "Read"))])
async def list_refunds(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_refunds(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
