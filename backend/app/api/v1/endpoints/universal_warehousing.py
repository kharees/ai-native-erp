import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.crud import universal_warehousing as crud
from app.schemas import universal_warehousing as schemas
from app.schemas.universal_inventory import PaginatedResponse
from app.middleware.tenant_auth import TenantIDDep, UserIDDep
from app.middleware.rbac import RequirePermission
from app.services.audit import AuditLogger

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

def _not_found(entity: str, id: uuid.UUID) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} '{id}' not found.")

def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

# -----------------
# Warehouses
# -----------------
@router.post("/warehouses", response_model=schemas.UniversalWarehouseResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalInventory", "Warehouses", "Create"))])
async def create_warehouse(payload: schemas.UniversalWarehouseCreate, tenant_id: TenantIDDep, db: DBDep):
    try:
        return await crud.create_warehouse(db, tenant_id, payload)
    except IntegrityError:
        raise _conflict(f"Warehouse Code '{payload.code}' already exists.")

@router.get("/warehouses", response_model=PaginatedResponse[schemas.UniversalWarehouseResponse], dependencies=[Depends(RequirePermission("UniversalInventory", "Warehouses", "Read"))])
async def list_warehouses(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0, search: str | None = None):
    items, total = await crud.list_warehouses(db, tenant_id, limit, offset, search)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/warehouses/{id}", response_model=schemas.UniversalWarehouseResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "Warehouses", "Read"))])
async def get_warehouse(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_warehouse(db, tenant_id, id)
    if not obj: raise _not_found("Warehouse", id)
    return obj

# -----------------
# Bins
# -----------------
@router.post("/bins", response_model=schemas.UniversalWarehouseBinResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalInventory", "Bins", "Create"))])
async def create_bin(payload: schemas.UniversalWarehouseBinCreate, tenant_id: TenantIDDep, db: DBDep):
    try:
        return await crud.create_bin(db, tenant_id, payload)
    except IntegrityError:
        raise _conflict(f"Bin Code '{payload.code}' already exists in this warehouse.")

@router.get("/bins", response_model=PaginatedResponse[schemas.UniversalWarehouseBinResponse], dependencies=[Depends(RequirePermission("UniversalInventory", "Bins", "Read"))])
async def list_bins(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0, warehouse_id: uuid.UUID | None = None, search: str | None = None):
    items, total = await crud.list_bins(db, tenant_id, limit, offset, warehouse_id, search)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.get("/bins/{id}", response_model=schemas.UniversalWarehouseBinResponse, dependencies=[Depends(RequirePermission("UniversalInventory", "Bins", "Read"))])
async def get_bin(id: uuid.UUID, tenant_id: TenantIDDep, db: DBDep):
    obj = await crud.get_bin(db, tenant_id, id)
    if not obj: raise _not_found("Bin", id)
    return obj

# -----------------
# Stock Engine
# -----------------
@router.post("/stock/transactions", response_model=schemas.StockTransactionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalInventory", "Stock", "Create"))])
async def create_stock_transaction(request: Request, payload: schemas.StockMovementRequest, tenant_id: TenantIDDep, user_id: UserIDDep, db: DBDep):
    try:
        txn = await crud.execute_stock_movement(db, tenant_id, user_id, payload)
        await AuditLogger.log_action(
            db=db,
            request=request,
            action_category="Inventory",
            action_type=f"Stock_{payload.transaction_type}",
            resource_id=str(txn.id),
            new_values=payload.model_dump(mode='json')
        )
        await db.commit() # Commit the audit log
        return txn
    except IntegrityError:
        raise _conflict("Transaction failed: Negative stock prevented or invalid constraints.")

@router.post("/stock/reserve", response_model=schemas.StockBalanceResponse, status_code=status.HTTP_200_OK, dependencies=[Depends(RequirePermission("UniversalInventory", "Stock", "Update"))])
async def reserve_stock(request: Request, payload: schemas.StockMovementRequest, tenant_id: TenantIDDep, db: DBDep):
    try:
        balance = await crud.reserve_stock(db, tenant_id, payload)
        await AuditLogger.log_action(
            db=db,
            request=request,
            action_category="Inventory",
            action_type="Stock_Reservation",
            resource_id=str(balance.id),
            new_values=payload.model_dump(mode='json')
        )
        await db.commit()
        return balance
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/stock/allocate", response_model=schemas.StockBalanceResponse, status_code=status.HTTP_200_OK, dependencies=[Depends(RequirePermission("UniversalInventory", "Stock", "Update"))])
async def allocate_stock(request: Request, payload: schemas.StockMovementRequest, tenant_id: TenantIDDep, db: DBDep):
    try:
        balance = await crud.allocate_stock(db, tenant_id, payload)
        await AuditLogger.log_action(
            db=db,
            request=request,
            action_category="Inventory",
            action_type="Stock_Allocation",
            resource_id=str(balance.id),
            new_values=payload.model_dump(mode='json')
        )
        await db.commit()
        return balance
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
