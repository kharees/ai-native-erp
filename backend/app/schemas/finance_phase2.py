from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal

# --- AR Schemas ---
class ARLedgerBase(BaseModel):
    customer_id: UUID
    outstanding_amount: Decimal = Field(default=Decimal("0.00"), max_digits=15, decimal_places=2)
    credit_limit: Decimal = Field(default=Decimal("0.00"), max_digits=15, decimal_places=2)
    is_bad_debt: bool = False

class ARLedgerCreate(ARLedgerBase):
    tenant_id: UUID

class ARLedgerOut(ARLedgerBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ARCollectionBase(BaseModel):
    customer_id: UUID
    status: str = Field(default="PROMISED_TO_PAY", max_length=50)
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None

class ARCollectionCreate(ARCollectionBase):
    tenant_id: UUID

class ARCollectionOut(ARCollectionBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ARReceiptBase(BaseModel):
    customer_id: UUID
    receipt_number: str = Field(..., max_length=100)
    amount: Decimal
    payment_mode: str = Field(..., max_length=50)
    reference: Optional[str] = Field(None, max_length=100)

class ARReceiptCreate(ARReceiptBase):
    tenant_id: UUID
    unallocated_amount: Decimal

class ARReceiptOut(ARReceiptBase):
    id: UUID
    tenant_id: UUID
    unallocated_amount: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- AP Schemas ---
class APVendorBase(BaseModel):
    name: str = Field(..., max_length=255)
    email: Optional[str] = Field(None, max_length=320)
    phone: Optional[str] = Field(None, max_length=32)
    tax_number: Optional[str] = Field(None, max_length=50)
    outstanding_amount: Decimal = Field(default=Decimal("0.00"), max_digits=15, decimal_places=2)

class APVendorCreate(APVendorBase):
    tenant_id: UUID

class APVendorOut(APVendorBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class APBillBase(BaseModel):
    vendor_id: UUID
    bill_number: str = Field(..., max_length=100)
    amount: Decimal
    due_date: datetime
    status: str = Field(default="UNPAID", max_length=50)

class APBillCreate(APBillBase):
    tenant_id: UUID

class APBillOut(APBillBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class APPaymentBase(BaseModel):
    vendor_id: UUID
    payment_number: str = Field(..., max_length=100)
    amount: Decimal
    payment_mode: str = Field(..., max_length=50)
    reference: Optional[str] = Field(None, max_length=100)

class APPaymentCreate(APPaymentBase):
    tenant_id: UUID
    unallocated_amount: Decimal

class APPaymentOut(APPaymentBase):
    id: UUID
    tenant_id: UUID
    unallocated_amount: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Bank & Cash Schemas ---
class BankReconciliationBase(BaseModel):
    bank_account_id: UUID
    statement_date: datetime
    statement_balance: Decimal
    system_balance: Decimal
    status: str = Field(default="PENDING", max_length=50)

class BankReconciliationCreate(BankReconciliationBase):
    tenant_id: UUID

class BankReconciliationOut(BankReconciliationBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CashAccountBase(BaseModel):
    name: str = Field(..., max_length=128)
    is_petty_cash: bool = False
    balance: Decimal = Field(default=Decimal("0.00"), max_digits=15, decimal_places=2)

class CashAccountCreate(CashAccountBase):
    tenant_id: UUID

class CashAccountOut(CashAccountBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Expense Schemas ---
class ExpenseCategoryBase(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None

class ExpenseCategoryCreate(ExpenseCategoryBase):
    tenant_id: UUID

class ExpenseCategoryOut(ExpenseCategoryBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ExpenseClaimBase(BaseModel):
    category_id: UUID
    amount: Decimal
    description: Optional[str] = None
    status: str = Field(default="SUBMITTED", max_length=50)

class ExpenseClaimCreate(ExpenseClaimBase):
    tenant_id: UUID
    user_id: UUID

class ExpenseClaimOut(ExpenseClaimBase):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    approved_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
