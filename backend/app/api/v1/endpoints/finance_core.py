from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sqlalchemy import select

from app.core.database import get_db
from app.middleware.tenant_auth import get_verified_tenant_id
from app.middleware.rbac import RequirePermission
from app.services.audit import AuditLogger
from app.crud.crud_finance_core import finance_core
from app.models.users import UserProfile
from app.schemas.finance_core import (
    AccountGroupCreate, AccountGroupOut, AccountGroupUpdate,
    AccountCreate, AccountOut, AccountUpdate,
    JournalVoucherCreate, JournalVoucherOut, JournalVoucherUpdate
)

log = structlog.get_logger(__name__)
router = APIRouter()

def get_user_id(request: Request) -> UUID:
    # Assuming user_id is in request.state from auth middleware
    # Defaulting to a placeholder for now if not present, but should raise in production
    user_id = getattr(request.state, "user_id", None)
    return user_id

# --- Account Groups ---

@router.post("/account-groups", response_model=AccountGroupOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "AccountGroup", "Create"))])
async def create_account_group(
    request: Request,
    payload: AccountGroupCreate,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_core.create_account_group(db, payload)
    await AuditLogger.log_action(
        db=db, request=request, action_category="FINANCE", action_type="CREATE_ACCOUNT_GROUP",
        resource_id=str(result.id)
    )
    await db.flush()
    return result

@router.get("/account-groups", response_model=List[AccountGroupOut], dependencies=[Depends(RequirePermission("Finance", "AccountGroup", "Read"))])
async def list_account_groups(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    return await finance_core.get_account_groups(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.get("/account-groups/{id}", response_model=AccountGroupOut, dependencies=[Depends(RequirePermission("Finance", "AccountGroup", "Read"))])
async def get_account_group(request: Request, id: UUID, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    obj = await finance_core.get_account_group(db, id, tenant_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Account group '{id}' not found.")
    return obj

@router.patch("/account-groups/{id}", response_model=AccountGroupOut, dependencies=[Depends(RequirePermission("Finance", "AccountGroup", "Update"))])
async def update_account_group(request: Request, id: UUID, payload: AccountGroupUpdate, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    obj = await finance_core.get_account_group(db, id, tenant_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Account group '{id}' not found.")
    result = await finance_core.update_account_group(db, obj, payload)
    await AuditLogger.log_action(
        db=db, request=request, action_category="FINANCE", action_type="UPDATE_ACCOUNT_GROUP",
        resource_id=str(result.id)
    )
    await db.flush()
    return result

# --- Accounts (Chart of Accounts) ---

@router.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "Account", "Create"))])
async def create_account(
    request: Request,
    payload: AccountCreate,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_core.create_account(db, payload)
    await AuditLogger.log_action(
        db=db, request=request, action_category="FINANCE", action_type="CREATE_ACCOUNT",
        resource_id=str(result.id)
    )
    await db.flush()
    return result

@router.get("/accounts", response_model=List[AccountOut], dependencies=[Depends(RequirePermission("Finance", "Account", "Read"))])
async def list_accounts(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    return await finance_core.get_accounts(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.get("/accounts/{id}", response_model=AccountOut, dependencies=[Depends(RequirePermission("Finance", "Account", "Read"))])
async def get_account(request: Request, id: UUID, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    obj = await finance_core.get_account(db, id, tenant_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Account '{id}' not found.")
    return obj

@router.patch("/accounts/{id}", response_model=AccountOut, dependencies=[Depends(RequirePermission("Finance", "Account", "Update"))])
async def update_account(request: Request, id: UUID, payload: AccountUpdate, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    obj = await finance_core.get_account(db, id, tenant_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Account '{id}' not found.")
    result = await finance_core.update_account(db, obj, payload)
    await AuditLogger.log_action(
        db=db, request=request, action_category="FINANCE", action_type="UPDATE_ACCOUNT",
        resource_id=str(result.id)
    )
    await db.flush()
    return result

# --- Journal Vouchers ---

@router.post("/journal-vouchers", response_model=JournalVoucherOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "Journal", "Create"))])
async def create_journal_voucher(
    request: Request,
    payload: JournalVoucherCreate,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    user_id = get_user_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_core.create_journal_voucher(db, payload, user_id=user_id)
    await AuditLogger.log_action(
        db=db, request=request, action_category="FINANCE", action_type="CREATE_JOURNAL_VOUCHER",
        resource_id=str(result.id)
    )
    await db.flush()
    return result

@router.get("/journals", response_model=List[JournalVoucherOut], dependencies=[Depends(RequirePermission("Finance", "Journal", "Read"))])
async def list_journal_vouchers(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    return await finance_core.get_journal_vouchers(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.get("/journals/{id}", response_model=JournalVoucherOut, dependencies=[Depends(RequirePermission("Finance", "Journal", "Read"))])
async def get_journal_voucher(request: Request, id: UUID, db: AsyncSession = Depends(get_db)):
    tenant_id = await get_verified_tenant_id(request)
    obj = await finance_core.get_journal_voucher(db, id, tenant_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Journal voucher '{id}' not found.")
    return obj

@router.post("/journals/{voucher_id}/approve", response_model=JournalVoucherOut, dependencies=[Depends(RequirePermission("Finance", "Journal", "Approve"))])
async def approve_journal_voucher(
    request: Request,
    voucher_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = await get_verified_tenant_id(request)
    user_id = get_user_id(request)

    # JournalVoucher.approved_by is a FK to user_profiles.id, not
    # user_accounts.id — resolve the tenant-scoped profile for the calling
    # account before handing it to the CRUD layer. Passing the raw JWT `sub`
    # (an account id) here throws a FK violation on every approval.
    approver_profile_id = None
    if user_id:
        prof_stmt = select(UserProfile.id).where(
            UserProfile.user_id == user_id, UserProfile.tenant_id == tenant_id
        )
        approver_profile_id = (await db.execute(prof_stmt)).scalar_one_or_none()

    result = await finance_core.approve_journal_voucher(db, id=voucher_id, tenant_id=tenant_id, user_id=approver_profile_id)
    await AuditLogger.log_action(
        db=db, request=request, action_category="FINANCE", action_type="APPROVE_JOURNAL_VOUCHER",
        resource_id=str(result.id)
    )
    await db.flush()
    return result
