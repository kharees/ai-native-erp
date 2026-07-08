from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta

# Bank Account
class UniversalBankAccountBase(BaseModel):
    bank_name: str = Field(..., max_length=128)
    account_number: str = Field(..., max_length=64)
    account_type: str = Field("CURRENT", max_length=32)
    ifsc_code: str = Field(..., max_length=32)
    branch_name: str | None = Field(None, max_length=128)
    is_active: bool = True
    current_balance: float = Field(0.0)

class UniversalBankAccountCreate(UniversalBankAccountBase):
    pass

class UniversalBankAccountUpdate(BaseModel):
    bank_name: str | None = Field(None, max_length=128)
    account_number: str | None = Field(None, max_length=64)
    account_type: str | None = Field(None, max_length=32)
    ifsc_code: str | None = Field(None, max_length=32)
    branch_name: str | None = Field(None, max_length=128)
    is_active: bool | None = None

class UniversalBankAccountResponse(UniversalBankAccountBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Bank Voucher
class UniversalBankVoucherBase(BaseModel):
    bank_account_id: uuid.UUID
    voucher_number: str = Field(..., max_length=64)
    voucher_type: str = Field(..., max_length=32)
    amount: float = Field(...)
    reference_number: str | None = Field(None, max_length=128)
    remarks: str | None = None

class UniversalBankVoucherCreate(UniversalBankVoucherBase):
    pass

class UniversalBankVoucherUpdate(BaseModel):
    remarks: str | None = None

class UniversalBankVoucherResponse(UniversalBankVoucherBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    transaction_date: datetime
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
