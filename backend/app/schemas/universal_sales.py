from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
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

# Customer Price List
class UniversalCustomerPriceListBase(BaseModel):
    customer_group_id: uuid.UUID
    item_id: uuid.UUID
    price: float = Field(..., ge=0)

class UniversalCustomerPriceListCreate(UniversalCustomerPriceListBase):
    pass

class UniversalCustomerPriceListUpdate(BaseModel):
    price: float | None = Field(None, ge=0)

class UniversalCustomerPriceListResponse(UniversalCustomerPriceListBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Sales Quotation Item
class UniversalSalesQuotationItemBase(BaseModel):
    item_id: uuid.UUID
    # quantity is Numeric(15, 4) on the DB side but deliberately stays
    # float, not Decimal -- it's a physical quantity, not money (same
    # convention as schemas/universal_invoices.py's item quantity field).
    quantity: float = Field(..., gt=0)
    # Decimal, matching UniversalSalesQuotationItem.unit_price's
    # Numeric(15, 2) column exactly -- money must never pass through a
    # Python float (binary floating point can't represent most base-10
    # fractions exactly). Same convention as schemas/sales_fulfillment.py's
    # QuotationLineItem.unit_price and schemas/universal_invoices.py.
    unit_price: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2)

class UniversalSalesQuotationItemCreate(UniversalSalesQuotationItemBase):
    pass

class UniversalSalesQuotationItemResponse(UniversalSalesQuotationItemBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    quotation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Sales Quotation
class UniversalSalesQuotationBase(BaseModel):
    customer_id: uuid.UUID
    quotation_number: str = Field(..., max_length=64)
    status: str = Field("DRAFT", max_length=32)
    valid_until: datetime | None = None
    # Decimal, matching UniversalSalesQuotation.total_amount's
    # Numeric(15, 2) column exactly -- see UniversalSalesQuotationItemBase.
    # unit_price above for the full rationale.
    total_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=15, decimal_places=2)

class UniversalSalesQuotationCreate(UniversalSalesQuotationBase):
    items: list[UniversalSalesQuotationItemCreate]

class UniversalSalesQuotationUpdate(BaseModel):
    status: str | None = Field(None, max_length=32)
    valid_until: datetime | None = None
    # total_amount and items would be handled by specific endpoints if needed

class UniversalSalesQuotationResponse(UniversalSalesQuotationBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    revision_number: int
    created_at: datetime
    updated_at: datetime
    items: list[UniversalSalesQuotationItemResponse] = []
    model_config = ConfigDict(from_attributes=True)

# Sales Order Item
class UniversalSalesOrderItemBase(BaseModel):
    item_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)

class UniversalSalesOrderItemCreate(UniversalSalesOrderItemBase):
    pass

class UniversalSalesOrderItemResponse(UniversalSalesOrderItemBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    order_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Sales Order
class UniversalSalesOrderBase(BaseModel):
    customer_id: uuid.UUID
    quotation_id: uuid.UUID | None = None
    order_number: str = Field(..., max_length=64)
    status: str = Field("PENDING", max_length=32)
    approval_status: str = Field("PENDING", max_length=32)
    total_amount: float = Field(0.0, ge=0)

class UniversalSalesOrderCreate(UniversalSalesOrderBase):
    items: list[UniversalSalesOrderItemCreate]

class UniversalSalesOrderUpdate(BaseModel):
    status: str | None = Field(None, max_length=32)
    approval_status: str | None = Field(None, max_length=32)

class UniversalSalesOrderResponse(UniversalSalesOrderBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    items: list[UniversalSalesOrderItemResponse] = []
    model_config = ConfigDict(from_attributes=True)
