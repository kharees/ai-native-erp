import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_invoices as crud
from app.schemas import universal_invoices as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission
from app.services.idempotency import claim_idempotency_key, complete_idempotency_key

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]

def _not_found(entity: str, id: uuid.UUID) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} '{id}' not found.")

@router.post("/proforma", response_model=schemas.UniversalProformaInvoiceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Invoices", "Create"))])
async def create_proforma_invoice(payload: schemas.UniversalProformaInvoiceCreate, tenant_id: TenantIDDep, db: DBDep, idempotency_key: IdempotencyKeyHeader = None):
    claim = await claim_idempotency_key(db, tenant_id, "invoices.proforma", idempotency_key)
    if claim.replay_response is not None:
        return claim.replay_response
    if claim.conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A request with this Idempotency-Key is already being processed.")

    obj = await crud.create_proforma_invoice(db, tenant_id, payload)

    if claim.should_complete:
        response_body = jsonable_encoder(schemas.UniversalProformaInvoiceResponse.model_validate(obj))
        await complete_idempotency_key(db, tenant_id, "invoices.proforma", idempotency_key, obj.id, response_body)

    return obj

@router.get("/proforma", response_model=schemas.PaginatedResponse[schemas.UniversalProformaInvoiceResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Invoices", "Read"))])
async def list_proforma_invoices(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_proforma_invoices(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/proforma/{id}", response_model=schemas.UniversalProformaInvoiceResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Invoices", "Read"))])
async def get_proforma_invoice(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_proforma_invoice(db, tenant_id, id)
    if not obj: raise _not_found("Proforma Invoice", id)
    return obj

@router.post("/tax", response_model=schemas.UniversalTaxInvoiceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Invoices", "Create"))])
async def create_tax_invoice(payload: schemas.UniversalTaxInvoiceCreate, tenant_id: TenantIDDep, db: DBDep, idempotency_key: IdempotencyKeyHeader = None):
    claim = await claim_idempotency_key(db, tenant_id, "invoices.tax", idempotency_key)
    if claim.replay_response is not None:
        return claim.replay_response
    if claim.conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A request with this Idempotency-Key is already being processed.")

    obj = await crud.create_tax_invoice(db, tenant_id, payload)

    if claim.should_complete:
        response_body = jsonable_encoder(schemas.UniversalTaxInvoiceResponse.model_validate(obj))
        await complete_idempotency_key(db, tenant_id, "invoices.tax", idempotency_key, obj.id, response_body)

    return obj

@router.get("/tax", response_model=schemas.PaginatedResponse[schemas.UniversalTaxInvoiceResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Invoices", "Read"))])
async def list_tax_invoices(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_tax_invoices(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/tax/{id}", response_model=schemas.UniversalTaxInvoiceResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Invoices", "Read"))])
async def get_tax_invoice(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_tax_invoice(db, tenant_id, id)
    if not obj: raise _not_found("Tax Invoice", id)
    return obj
