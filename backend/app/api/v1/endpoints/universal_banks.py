import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import universal_banks as crud
from app.schemas import universal_banks as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.post("/accounts", response_model=schemas.UniversalBankAccountResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Banks", "Create"))])
async def create_bank_account(payload: schemas.UniversalBankAccountCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_bank_account(db, tenant_id, payload)

@router.get("/accounts", response_model=schemas.PaginatedResponse[schemas.UniversalBankAccountResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Banks", "Read"))])
async def list_bank_accounts(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_bank_accounts(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}

@router.post("/vouchers", response_model=schemas.UniversalBankVoucherResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("UniversalBilling", "Banks", "Create"))])
async def create_bank_voucher(payload: schemas.UniversalBankVoucherCreate, tenant_id: TenantIDDep, db: DBDep):
    return await crud.create_bank_voucher(db, tenant_id, payload)

@router.get("/vouchers", response_model=schemas.PaginatedResponse[schemas.UniversalBankVoucherResponse], dependencies=[Depends(RequirePermission("UniversalBilling", "Banks", "Read"))])
async def list_bank_vouchers(tenant_id: TenantIDDep, db: DBDep, limit: int = 20, offset: int = 0):
    items, total = await crud.list_bank_vouchers(db, tenant_id, limit, offset)
    return {"items": items, "meta": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + len(items)) < total}}
