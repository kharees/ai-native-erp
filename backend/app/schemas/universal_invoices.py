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

# Proforma Invoice Item
class UniversalProformaInvoiceItemBase(BaseModel):
    item_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    cgst_amount: float = Field(0.0, ge=0)
    sgst_amount: float = Field(0.0, ge=0)
    igst_amount: float = Field(0.0, ge=0)
    line_total: float = Field(..., ge=0)

class UniversalProformaInvoiceItemCreate(UniversalProformaInvoiceItemBase):
    pass

class UniversalProformaInvoiceItemResponse(UniversalProformaInvoiceItemBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    pi_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Proforma Invoice
class UniversalProformaInvoiceBase(BaseModel):
    customer_id: uuid.UUID
    sales_order_id: uuid.UUID | None = None
    pi_number: str = Field(..., max_length=64)
    status: str = Field("DRAFT", max_length=32)
    currency: str = Field("INR", max_length=3)
    is_tax_inclusive: bool = False
    subtotal: float = Field(0.0, ge=0)
    total_tax: float = Field(0.0, ge=0)
    total_amount: float = Field(0.0, ge=0)

class UniversalProformaInvoiceCreate(UniversalProformaInvoiceBase):
    items: list[UniversalProformaInvoiceItemCreate]

class UniversalProformaInvoiceUpdate(BaseModel):
    status: str | None = Field(None, max_length=32)

class UniversalProformaInvoiceResponse(UniversalProformaInvoiceBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    revision_number: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Tax Invoice Item
class UniversalTaxInvoiceItemBase(BaseModel):
    item_id: uuid.UUID
    hsn_sac_code: str | None = Field(None, max_length=32)
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    cgst_amount: float = Field(0.0, ge=0)
    sgst_amount: float = Field(0.0, ge=0)
    igst_amount: float = Field(0.0, ge=0)
    line_total: float = Field(..., ge=0)

class UniversalTaxInvoiceItemCreate(UniversalTaxInvoiceItemBase):
    pass

class UniversalTaxInvoiceItemResponse(UniversalTaxInvoiceItemBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Tax Invoice
class UniversalTaxInvoiceBase(BaseModel):
    customer_id: uuid.UUID
    sales_order_id: uuid.UUID | None = None
    invoice_number: str = Field(..., max_length=64)
    status: str = Field("DRAFT", max_length=32)
    currency: str = Field("INR", max_length=3)
    is_tax_inclusive: bool = False
    subtotal: float = Field(0.0, ge=0)
    total_cgst: float = Field(0.0, ge=0)
    total_sgst: float = Field(0.0, ge=0)
    total_igst: float = Field(0.0, ge=0)
    tds_amount: float = Field(0.0, ge=0)
    total_amount: float = Field(0.0, ge=0)

class UniversalTaxInvoiceCreate(UniversalTaxInvoiceBase):
    items: list[UniversalTaxInvoiceItemCreate]

class UniversalTaxInvoiceUpdate(BaseModel):
    status: str | None = Field(None, max_length=32)

class UniversalTaxInvoiceResponse(UniversalTaxInvoiceBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
