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

# Credit Note Item
class UniversalCreditNoteItemBase(BaseModel):
    item_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    line_total: float = Field(..., ge=0)

class UniversalCreditNoteItemCreate(UniversalCreditNoteItemBase):
    pass

class UniversalCreditNoteItemResponse(UniversalCreditNoteItemBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    note_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Credit Note
class UniversalCreditNoteBase(BaseModel):
    customer_id: uuid.UUID
    tax_invoice_id: uuid.UUID | None = None
    note_number: str = Field(..., max_length=64)
    reason: str | None = None
    status: str = Field("DRAFT", max_length=32)
    total_amount: float = Field(0.0, ge=0)

class UniversalCreditNoteCreate(UniversalCreditNoteBase):
    items: list[UniversalCreditNoteItemCreate]

class UniversalCreditNoteUpdate(BaseModel):
    status: str | None = Field(None, max_length=32)
    reason: str | None = None

class UniversalCreditNoteResponse(UniversalCreditNoteBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Debit Note Item
class UniversalDebitNoteItemBase(BaseModel):
    item_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    line_total: float = Field(..., ge=0)

class UniversalDebitNoteItemCreate(UniversalDebitNoteItemBase):
    pass

class UniversalDebitNoteItemResponse(UniversalDebitNoteItemBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    note_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Debit Note
class UniversalDebitNoteBase(BaseModel):
    customer_id: uuid.UUID
    tax_invoice_id: uuid.UUID | None = None
    note_number: str = Field(..., max_length=64)
    reason: str | None = None
    status: str = Field("DRAFT", max_length=32)
    total_amount: float = Field(0.0, ge=0)

class UniversalDebitNoteCreate(UniversalDebitNoteBase):
    items: list[UniversalDebitNoteItemCreate]

class UniversalDebitNoteUpdate(BaseModel):
    status: str | None = Field(None, max_length=32)
    reason: str | None = None

class UniversalDebitNoteResponse(UniversalDebitNoteBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Sales Return Item
class UniversalSalesReturnItemBase(BaseModel):
    item_id: uuid.UUID
    quantity_returned: float = Field(..., gt=0)

class UniversalSalesReturnItemCreate(UniversalSalesReturnItemBase):
    pass

class UniversalSalesReturnItemResponse(UniversalSalesReturnItemBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    return_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Sales Return
class UniversalSalesReturnBase(BaseModel):
    customer_id: uuid.UUID
    delivery_challan_id: uuid.UUID | None = None
    return_number: str = Field(..., max_length=64)
    reason: str | None = None
    status: str = Field("PENDING", max_length=32)

class UniversalSalesReturnCreate(UniversalSalesReturnBase):
    items: list[UniversalSalesReturnItemCreate]

class UniversalSalesReturnUpdate(BaseModel):
    status: str | None = Field(None, max_length=32)
    reason: str | None = None

class UniversalSalesReturnResponse(UniversalSalesReturnBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
