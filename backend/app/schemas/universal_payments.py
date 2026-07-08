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

# Payment Receipt
class UniversalPaymentReceiptBase(BaseModel):
    customer_id: uuid.UUID
    bank_account_id: uuid.UUID | None = None
    receipt_number: str = Field(..., max_length=64)
    payment_mode: str = Field(..., max_length=32)
    reference_number: str | None = Field(None, max_length=128)
    amount_received: float = Field(..., gt=0)
    unallocated_amount: float = Field(..., ge=0)
    status: str = Field("CLEARED", max_length=32)

class UniversalPaymentReceiptCreate(UniversalPaymentReceiptBase):
    pass

class UniversalPaymentReceiptUpdate(BaseModel):
    status: str | None = Field(None, max_length=32)

class UniversalPaymentReceiptResponse(UniversalPaymentReceiptBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    payment_date: datetime
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Payment Allocation
class UniversalPaymentAllocationBase(BaseModel):
    receipt_id: uuid.UUID
    invoice_id: uuid.UUID
    allocated_amount: float = Field(..., gt=0)

class UniversalPaymentAllocationCreate(UniversalPaymentAllocationBase):
    pass

class UniversalPaymentAllocationResponse(UniversalPaymentAllocationBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Refund
class UniversalRefundBase(BaseModel):
    customer_id: uuid.UUID
    receipt_id: uuid.UUID | None = None
    credit_note_id: uuid.UUID | None = None
    bank_account_id: uuid.UUID | None = None
    refund_number: str = Field(..., max_length=64)
    payment_mode: str = Field(..., max_length=32)
    reference_number: str | None = Field(None, max_length=128)
    amount_refunded: float = Field(..., gt=0)
    status: str = Field("CLEARED", max_length=32)

class UniversalRefundCreate(UniversalRefundBase):
    pass

class UniversalRefundResponse(UniversalRefundBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    refund_date: datetime
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Customer Wallet
class UniversalCustomerWalletBase(BaseModel):
    customer_id: uuid.UUID
    balance: float = Field(0.0, ge=0)

class UniversalCustomerWalletResponse(UniversalCustomerWalletBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
