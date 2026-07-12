from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.finance_phase2 import (
    ARLedger, ARCollection, ARReceipt,
    APVendor, APBill, APPayment,
    BankReconciliation, CashAccount,
    ExpenseCategory, ExpenseClaim
)
from app.schemas.finance_phase2 import (
    ARLedgerCreate, ARCollectionCreate, ARReceiptCreate,
    APVendorCreate, APBillCreate, APPaymentCreate,
    BankReconciliationCreate, CashAccountCreate,
    ExpenseCategoryCreate, ExpenseClaimCreate
)

class CRUDFinancePhase2:
    # --- AR ---
    async def create_ar_ledger(self, db: AsyncSession, obj_in: ARLedgerCreate) -> ARLedger:
        db_obj = ARLedger(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_ar_ledgers(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[ARLedger]:
        result = await db.execute(select(ARLedger).where(ARLedger.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_ar_collection(self, db: AsyncSession, obj_in: ARCollectionCreate) -> ARCollection:
        db_obj = ARCollection(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_ar_collections(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[ARCollection]:
        result = await db.execute(select(ARCollection).where(ARCollection.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_ar_receipt(self, db: AsyncSession, obj_in: ARReceiptCreate) -> ARReceipt:
        db_obj = ARReceipt(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_ar_receipts(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[ARReceipt]:
        result = await db.execute(select(ARReceipt).where(ARReceipt.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    # --- AP ---
    async def create_ap_vendor(self, db: AsyncSession, obj_in: APVendorCreate) -> APVendor:
        db_obj = APVendor(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_ap_vendors(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[APVendor]:
        result = await db.execute(select(APVendor).where(APVendor.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_ap_bill(self, db: AsyncSession, obj_in: APBillCreate) -> APBill:
        db_obj = APBill(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_ap_bills(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[APBill]:
        result = await db.execute(select(APBill).where(APBill.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_ap_payment(self, db: AsyncSession, obj_in: APPaymentCreate) -> APPayment:
        db_obj = APPayment(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_ap_payments(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[APPayment]:
        result = await db.execute(select(APPayment).where(APPayment.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    # --- Bank & Cash ---
    async def create_cash_account(self, db: AsyncSession, obj_in: CashAccountCreate) -> CashAccount:
        db_obj = CashAccount(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_cash_accounts(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[CashAccount]:
        result = await db.execute(select(CashAccount).where(CashAccount.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())
        
    async def create_bank_reconciliation(self, db: AsyncSession, obj_in: BankReconciliationCreate) -> BankReconciliation:
        db_obj = BankReconciliation(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_bank_reconciliations(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[BankReconciliation]:
        result = await db.execute(select(BankReconciliation).where(BankReconciliation.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    # --- Expenses ---
    async def create_expense_category(self, db: AsyncSession, obj_in: ExpenseCategoryCreate) -> ExpenseCategory:
        db_obj = ExpenseCategory(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_expense_categories(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[ExpenseCategory]:
        result = await db.execute(select(ExpenseCategory).where(ExpenseCategory.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_expense_claim(self, db: AsyncSession, obj_in: ExpenseClaimCreate) -> ExpenseClaim:
        db_obj = ExpenseClaim(**obj_in.model_dump())
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_expense_claims(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[ExpenseClaim]:
        result = await db.execute(select(ExpenseClaim).where(ExpenseClaim.tenant_id == tenant_id).offset(skip).limit(limit))
        return list(result.scalars().all())

finance_phase2 = CRUDFinancePhase2()
