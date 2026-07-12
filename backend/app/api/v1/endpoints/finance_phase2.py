from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.middleware.rbac import RequirePermission
from app.services.audit import AuditLogger
from app.crud.crud_finance_phase2 import finance_phase2
from app.schemas.finance_phase2 import (
    ARLedgerCreate, ARLedgerOut,
    ARCollectionCreate, ARCollectionOut,
    ARReceiptCreate, ARReceiptOut,
    APVendorCreate, APVendorOut,
    APBillCreate, APBillOut,
    APPaymentCreate, APPaymentOut,
    BankReconciliationCreate, BankReconciliationOut,
    CashAccountCreate, CashAccountOut,
    ExpenseCategoryCreate, ExpenseCategoryOut,
    ExpenseClaimCreate, ExpenseClaimOut
)

log = structlog.get_logger(__name__)
router = APIRouter()

def get_tenant_id(request: Request) -> UUID:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Missing tenant context")
    return tenant_id

def get_user_id(request: Request) -> UUID:
    return getattr(request.state, "user_id", None)

# --- Accounts Receivable ---
@router.post("/ar/ledgers", response_model=ARLedgerOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "ARLedger", "Create"))])
async def create_ar_ledger(request: Request, payload: ARLedgerCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase2.create_ar_ledger(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_AR_LEDGER", resource_id=str(result.id))
    await db.flush()
    return result

@router.get("/ar/ledgers", response_model=List[ARLedgerOut], dependencies=[Depends(RequirePermission("Finance", "ARLedger", "Read"))])
async def list_ar_ledgers(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    return await finance_phase2.get_ar_ledgers(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.post("/ar/collections", response_model=ARCollectionOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "ARCollection", "Create"))])
async def create_ar_collection(request: Request, payload: ARCollectionCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase2.create_ar_collection(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_AR_COLLECTION", resource_id=str(result.id))
    await db.flush()
    return result

@router.get("/ar/collections", response_model=List[ARCollectionOut], dependencies=[Depends(RequirePermission("Finance", "ARCollection", "Read"))])
async def list_ar_collections(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    return await finance_phase2.get_ar_collections(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.post("/ar/receipts", response_model=ARReceiptOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "ARReceipt", "Create"))])
async def create_ar_receipt(request: Request, payload: ARReceiptCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase2.create_ar_receipt(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_AR_RECEIPT", resource_id=str(result.id))
    await db.flush()
    return result

@router.get("/ar/receipts", response_model=List[ARReceiptOut], dependencies=[Depends(RequirePermission("Finance", "ARReceipt", "Read"))])
async def list_ar_receipts(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    return await finance_phase2.get_ar_receipts(db, tenant_id=tenant_id, skip=skip, limit=limit)

# --- Accounts Payable ---
@router.post("/ap/vendors", response_model=APVendorOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "APVendor", "Create"))])
async def create_ap_vendor(request: Request, payload: APVendorCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase2.create_ap_vendor(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_AP_VENDOR", resource_id=str(result.id))
    await db.flush()
    return result

@router.get("/ap/vendors", response_model=List[APVendorOut], dependencies=[Depends(RequirePermission("Finance", "APVendor", "Read"))])
async def list_ap_vendors(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    return await finance_phase2.get_ap_vendors(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.post("/ap/bills", response_model=APBillOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "APBill", "Create"))])
async def create_ap_bill(request: Request, payload: APBillCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase2.create_ap_bill(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_AP_BILL", resource_id=str(result.id))
    await db.flush()
    return result

@router.get("/ap/bills", response_model=List[APBillOut], dependencies=[Depends(RequirePermission("Finance", "APBill", "Read"))])
async def list_ap_bills(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    return await finance_phase2.get_ap_bills(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.post("/ap/payments", response_model=APPaymentOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "APPayment", "Create"))])
async def create_ap_payment(request: Request, payload: APPaymentCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase2.create_ap_payment(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_AP_PAYMENT", resource_id=str(result.id))
    await db.flush()
    return result

@router.get("/ap/payments", response_model=List[APPaymentOut], dependencies=[Depends(RequirePermission("Finance", "APPayment", "Read"))])
async def list_ap_payments(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    return await finance_phase2.get_ap_payments(db, tenant_id=tenant_id, skip=skip, limit=limit)

# --- Banking & Cash ---
@router.post("/cash-accounts", response_model=CashAccountOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "CashAccount", "Create"))])
async def create_cash_account(request: Request, payload: CashAccountCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase2.create_cash_account(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_CASH_ACCOUNT", resource_id=str(result.id))
    await db.flush()
    return result

@router.get("/cash-accounts", response_model=List[CashAccountOut], dependencies=[Depends(RequirePermission("Finance", "CashAccount", "Read"))])
async def list_cash_accounts(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    return await finance_phase2.get_cash_accounts(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.post("/banking/reconciliations", response_model=BankReconciliationOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "BankReconciliation", "Create"))])
async def create_bank_reconciliation(request: Request, payload: BankReconciliationCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase2.create_bank_reconciliation(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_BANK_RECONCILIATION", resource_id=str(result.id))
    await db.flush()
    return result

@router.get("/banking/reconciliations", response_model=List[BankReconciliationOut], dependencies=[Depends(RequirePermission("Finance", "BankReconciliation", "Read"))])
async def list_bank_reconciliations(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    return await finance_phase2.get_bank_reconciliations(db, tenant_id=tenant_id, skip=skip, limit=limit)

# --- Expenses ---
@router.post("/expenses/categories", response_model=ExpenseCategoryOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "ExpenseCategory", "Create"))])
async def create_expense_category(request: Request, payload: ExpenseCategoryCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    result = await finance_phase2.create_expense_category(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_EXPENSE_CATEGORY", resource_id=str(result.id))
    await db.flush()
    return result

@router.get("/expenses/categories", response_model=List[ExpenseCategoryOut], dependencies=[Depends(RequirePermission("Finance", "ExpenseCategory", "Read"))])
async def list_expense_categories(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    return await finance_phase2.get_expense_categories(db, tenant_id=tenant_id, skip=skip, limit=limit)

@router.post("/expenses/claims", response_model=ExpenseClaimOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Finance", "ExpenseClaim", "Create"))])
async def create_expense_claim(request: Request, payload: ExpenseClaimCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")
    payload.user_id = get_user_id(request) # Force context user
    result = await finance_phase2.create_expense_claim(db, payload)
    await AuditLogger.log_action(db=db, request=request, action_category="FINANCE", action_type="CREATE_EXPENSE_CLAIM", resource_id=str(result.id))
    await db.flush()
    return result

@router.get("/expenses/claims", response_model=List[ExpenseClaimOut], dependencies=[Depends(RequirePermission("Finance", "ExpenseClaim", "Read"))])
async def list_expense_claims(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tenant_id = get_tenant_id(request)
    return await finance_phase2.get_expense_claims(db, tenant_id=tenant_id, skip=skip, limit=limit)
