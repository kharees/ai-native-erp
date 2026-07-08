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

# Shipping Courier
class UniversalShippingCourierBase(BaseModel):
    courier_name: str = Field(..., max_length=128)
    tracking_url_template: str | None = Field(None, max_length=256)
    is_active: bool = True

class UniversalShippingCourierCreate(UniversalShippingCourierBase):
    pass

class UniversalShippingCourierUpdate(BaseModel):
    courier_name: str | None = Field(None, max_length=128)
    tracking_url_template: str | None = Field(None, max_length=256)
    is_active: bool | None = None

class UniversalShippingCourierResponse(UniversalShippingCourierBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Order Dispatch
class UniversalOrderDispatchBase(BaseModel):
    sales_order_id: uuid.UUID
    courier_id: uuid.UUID | None = None
    tracking_number: str | None = Field(None, max_length=128)
    shipping_charges: float = Field(0.0, ge=0)
    dispatch_status: str = Field("PENDING", max_length=32)

class UniversalOrderDispatchCreate(UniversalOrderDispatchBase):
    pass

class UniversalOrderDispatchUpdate(BaseModel):
    dispatch_status: str | None = Field(None, max_length=32)
    tracking_number: str | None = Field(None, max_length=128)

class UniversalOrderDispatchResponse(UniversalOrderDispatchBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    dispatched_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
