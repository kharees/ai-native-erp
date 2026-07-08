import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_returns as crud
from app.schemas import universal_returns as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

def _not_found(entity: str, id: uuid.UUID) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} '{id}' not found.")

@router.post("/credit-notes", response_model=schemas.UniversalCreditNoteResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Returns", "Create"))])
async def create_credit_note(payload: schemas.UniversalCreditNoteCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_credit_note(db, tenant_id, payload)

@router.get("/credit-notes", response_model=schemas.PaginatedResponse[schemas.UniversalCreditNoteResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Returns", "Read"))])
async def list_credit_notes(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_credit_notes(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.post("/debit-notes", response_model=schemas.UniversalDebitNoteResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Returns", "Create"))])
async def create_debit_note(payload: schemas.UniversalDebitNoteCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_debit_note(db, tenant_id, payload)

@router.get("/debit-notes", response_model=schemas.PaginatedResponse[schemas.UniversalDebitNoteResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Returns", "Read"))])
async def list_debit_notes(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_debit_notes(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.post("/sales-returns", response_model=schemas.UniversalSalesReturnResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Returns", "Create"))])
async def create_sales_return(payload: schemas.UniversalSalesReturnCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_sales_return(db, tenant_id, payload)

@router.get("/sales-returns", response_model=schemas.PaginatedResponse[schemas.UniversalSalesReturnResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Returns", "Read"))])
async def list_sales_returns(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_sales_returns(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
