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

# Delivery Challan Item
class UniversalDeliveryChallanItemBase(BaseModel):
    item_id: uuid.UUID
    quantity_dispatched: float = Field(..., gt=0)

class UniversalDeliveryChallanItemCreate(UniversalDeliveryChallanItemBase):
    pass

class UniversalDeliveryChallanItemResponse(UniversalDeliveryChallanItemBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    challan_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Delivery Challan
class UniversalDeliveryChallanBase(BaseModel):
    customer_id: uuid.UUID
    sales_order_id: uuid.UUID | None = None
    tax_invoice_id: uuid.UUID | None = None
    challan_number: str = Field(..., max_length=64)
    status: str = Field("DRAFT", max_length=32)
    dispatch_date: datetime | None = None
    vehicle_number: str | None = Field(None, max_length=64)

class UniversalDeliveryChallanCreate(UniversalDeliveryChallanBase):
    items: list[UniversalDeliveryChallanItemCreate]

class UniversalDeliveryChallanUpdate(BaseModel):
    status: str | None = Field(None, max_length=32)
    dispatch_date: datetime | None = None
    vehicle_number: str | None = Field(None, max_length=64)

class UniversalDeliveryChallanResponse(UniversalDeliveryChallanBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Packing Slip Item
class UniversalPackingSlipItemBase(BaseModel):
    item_id: uuid.UUID
    quantity_packed: float = Field(..., gt=0)

class UniversalPackingSlipItemCreate(UniversalPackingSlipItemBase):
    pass

class UniversalPackingSlipItemResponse(UniversalPackingSlipItemBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    slip_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Packing Slip
class UniversalPackingSlipBase(BaseModel):
    challan_id: uuid.UUID | None = None
    slip_number: str = Field(..., max_length=64)
    package_count: int = Field(1, ge=1)
    total_weight: float | None = Field(None, ge=0)

class UniversalPackingSlipCreate(UniversalPackingSlipBase):
    items: list[UniversalPackingSlipItemCreate]

class UniversalPackingSlipUpdate(BaseModel):
    package_count: int | None = Field(None, ge=1)
    total_weight: float | None = Field(None, ge=0)

class UniversalPackingSlipResponse(UniversalPackingSlipBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
