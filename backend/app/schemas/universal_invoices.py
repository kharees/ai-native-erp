from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

# Every monetary field below is backed by a Postgres Numeric(15, 2) column
# (see app/models/universal_invoices.py) -- Decimal end to end, matching
# that column type exactly, is deliberate. Money must never pass through a
# Python float: binary floating point cannot represent most base-10
# fractions exactly (0.1 + 0.2 != 0.3), and this codebase has already been
# bitten by that class of bug in payment/banking code. quantity fields are
# NOT included here (Numeric(15, 4), not money) -- see
# app/services/sales_fulfillment.py's module docstring for how quantity
# (float) and these Decimal fields interoperate safely.

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
    unit_price: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2)
    cgst_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    sgst_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    igst_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    line_total: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2)

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
    subtotal: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    total_tax: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    total_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)

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
    items: list[UniversalProformaInvoiceItemResponse] = []
    model_config = ConfigDict(from_attributes=True)

# Tax Invoice Item
class UniversalTaxInvoiceItemBase(BaseModel):
    item_id: uuid.UUID
    hsn_sac_code: str | None = Field(None, max_length=32)
    quantity: float = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2)
    cgst_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    sgst_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    igst_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    line_total: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2)

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
    # Optional, not required: for invoices going through
    # create_invoice_with_stock_deduction (app/services/sales_fulfillment.py),
    # this is always server-generated inside the same atomic transaction as
    # the invoice row itself (GST-compliant, gapless, per-financial-year
    # sequential numbering -- see app/crud/universal_numbering.py) and any
    # caller-supplied value here is ignored. Still accepted (and required in
    # practice) by the legacy direct /invoices/tax endpoint, which bypasses
    # that service and has no numbering of its own.
    invoice_number: str | None = Field(None, max_length=64)
    status: str = Field("DRAFT", max_length=32)
    currency: str = Field("INR", max_length=3)
    is_tax_inclusive: bool = False
    subtotal: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    total_cgst: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    total_sgst: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    total_igst: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    tds_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)
    total_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)

class UniversalTaxInvoiceCreate(UniversalTaxInvoiceBase):
    items: list[UniversalTaxInvoiceItemCreate]

class UniversalTaxInvoiceCreateWithStock(UniversalTaxInvoiceCreate):
    """create_invoice_with_stock_deduction's payload (app/services/
    sales_fulfillment.py) -- adds warehouse_id, which plain invoices don't
    carry anywhere. One warehouse per invoice (all lines deduct from the
    same location), not per line item. Never pass this straight into
    crud.universal_invoices.create_tax_invoice -- strip warehouse_id first
    (it's not a column on UniversalTaxInvoice); sales_fulfillment.py does
    this via model_dump(exclude={"warehouse_id"})."""
    warehouse_id: uuid.UUID

class UniversalTaxInvoiceUpdate(BaseModel):
    status: str | None = Field(None, max_length=32)

class UniversalTaxInvoiceResponse(UniversalTaxInvoiceBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    items: list[UniversalTaxInvoiceItemResponse] = []
    model_config = ConfigDict(from_attributes=True)
