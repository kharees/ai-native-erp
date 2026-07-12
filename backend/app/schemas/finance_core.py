from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.models.finance_core import AccountCategory, AccountStatus, JournalStatus

# --- AccountGroup Schemas ---
class AccountGroupBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    parent_id: Optional[UUID] = None
    category: AccountCategory
    description: Optional[str] = None
    is_active: bool = True

class AccountGroupCreate(AccountGroupBase):
    tenant_id: UUID

class AccountGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    parent_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class AccountGroupOut(AccountGroupBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Account Schemas ---
class AccountBase(BaseModel):
    group_id: UUID
    account_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    status: AccountStatus = AccountStatus.ACTIVE
    currency: str = Field("USD", max_length=3)
    is_reconciliation_account: bool = False

class AccountCreate(AccountBase):
    tenant_id: UUID

class AccountUpdate(BaseModel):
    group_id: Optional[UUID] = None
    account_code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=255)
    status: Optional[AccountStatus] = None
    currency: Optional[str] = Field(None, max_length=3)
    is_reconciliation_account: Optional[bool] = None
    # Optimistic-locking check (audit #36). Optional — omitting it skips
    # the check entirely (preserves the existing API contract for callers
    # that don't send it yet); pass the value from a prior AccountOut.version
    # to have concurrent edits rejected with 409 instead of silently
    # overwriting each other.
    expected_version: Optional[int] = None

class AccountOut(AccountBase):
    id: UUID
    tenant_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- JournalEntryLine Schemas ---
class JournalEntryLineBase(BaseModel):
    account_id: UUID
    debit: Decimal = Field(default=Decimal("0.00"), max_digits=15, decimal_places=2)
    credit: Decimal = Field(default=Decimal("0.00"), max_digits=15, decimal_places=2)
    description: Optional[str] = Field(None, max_length=255)
    cost_center_id: Optional[UUID] = None
    profit_center_id: Optional[UUID] = None

class JournalEntryLineCreate(JournalEntryLineBase):
    pass # voucher_id and tenant_id are set by service

class JournalEntryLineOut(JournalEntryLineBase):
    id: UUID
    tenant_id: UUID
    voucher_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- JournalVoucher Schemas ---
class JournalVoucherBase(BaseModel):
    voucher_number: str = Field(..., max_length=100)
    reference: Optional[str] = Field(None, max_length=255)
    entry_date: datetime
    status: JournalStatus = JournalStatus.DRAFT
    description: Optional[str] = None
    source_document_type: Optional[str] = Field(None, max_length=100)
    source_document_id: Optional[str] = Field(None, max_length=100)

class JournalVoucherCreate(JournalVoucherBase):
    tenant_id: UUID
    lines: List[JournalEntryLineCreate]

class JournalVoucherUpdate(BaseModel):
    reference: Optional[str] = Field(None, max_length=255)
    status: Optional[JournalStatus] = None
    description: Optional[str] = None
    # Reversing or modifying lines should generally go through a structured service/API, not generic update
    
class JournalVoucherOut(JournalVoucherBase):
    id: UUID
    tenant_id: UUID
    total_debit: Decimal
    total_credit: Decimal
    created_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    lines: List[JournalEntryLineOut] = []
    model_config = ConfigDict(from_attributes=True)
