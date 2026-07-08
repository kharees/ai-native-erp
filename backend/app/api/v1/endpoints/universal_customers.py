import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_customers as crud
from app.schemas import universal_customers as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

def _not_found(entity: str, id: uuid.UUID) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} '{id}' not found.")

@router.post("/", response_model=schemas.UniversalCustomerResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Customers", "Create"))])
async def create_customer(payload: schemas.UniversalCustomerCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_customer(db, tenant_id, payload)

@router.get("/", response_model=schemas.PaginatedResponse[schemas.UniversalCustomerResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Customers", "Read"))])
async def list_customers(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0, search: str | None = None):
    items, total = await crud.list_customers(db, tenant_id, limit, offset, search)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/{id}", response_model=schemas.UniversalCustomerResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Customers", "Read"))])
async def get_customer(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_customer(db, tenant_id, id)
    if not obj: raise _not_found("Customer", id)
    return obj

@router.patch("/{id}", response_model=schemas.UniversalCustomerResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Customers", "Update"))])
async def update_customer(id: uuid.UUID, payload: schemas.UniversalCustomerUpdate, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.update_customer(db, tenant_id, id, payload)
    if not obj: raise _not_found("Customer", id)
    return obj

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, dependencies=[Depends(RequirePermission("UniversalBilling", "Customers", "Delete"))])
async def delete_customer(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    if not await crud.delete_customer(db, tenant_id, id): raise _not_found("Customer", id)
