import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_sales as crud
from app.schemas import universal_sales as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

def _not_found(entity: str, id: uuid.UUID) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} '{id}' not found.")

@router.post("/quotations", response_model=schemas.UniversalSalesQuotationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Sales", "Create"))])
async def create_quotation(payload: schemas.UniversalSalesQuotationCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_quotation(db, tenant_id, payload)

@router.get("/quotations", response_model=schemas.PaginatedResponse[schemas.UniversalSalesQuotationResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Sales", "Read"))])
async def list_quotations(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_quotations(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/quotations/{id}", response_model=schemas.UniversalSalesQuotationResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Sales", "Read"))])
async def get_quotation(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_quotation(db, tenant_id, id)
    if not obj: raise _not_found("Quotation", id)
    return obj

@router.post("/orders", response_model=schemas.UniversalSalesOrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Sales", "Create"))])
async def create_order(payload: schemas.UniversalSalesOrderCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_order(db, tenant_id, payload)

@router.get("/orders", response_model=schemas.PaginatedResponse[schemas.UniversalSalesOrderResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Sales", "Read"))])
async def list_orders(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_orders(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/orders/{id}", response_model=schemas.UniversalSalesOrderResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Sales", "Read"))])
async def get_order(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_order(db, tenant_id, id)
    if not obj: raise _not_found("Order", id)
    return obj

@router.post("/orders/convert-from-quote/{quote_id}", response_model=schemas.UniversalSalesOrderResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Sales", "Create"))])
async def convert_from_quote(quote_id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.convert_from_quote(db, tenant_id, quote_id)
    if not obj: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quotation not found or not approved.")
    return obj

@router.post("/orders/{id}/approve", response_model=schemas.UniversalSalesOrderResponse, dependencies=[Depends(RequirePermission("UniversalBilling", "Sales", "Update"))])
async def approve_order(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.approve_order(db, tenant_id, id)
    if not obj: raise _not_found("Order", id)
    return obj

@router.post("/price-lists", response_model=schemas.UniversalCustomerPriceListResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Sales", "Create"))])
async def create_price_list(payload: schemas.UniversalCustomerPriceListCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_price_list(db, tenant_id, payload)

@router.get("/price-lists", response_model=schemas.PaginatedResponse[schemas.UniversalCustomerPriceListResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Sales", "Read"))])
async def list_price_lists(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_price_lists(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
