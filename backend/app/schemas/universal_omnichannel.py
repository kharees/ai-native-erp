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

# Channel Config
class UniversalChannelConfigurationBase(BaseModel):
    platform_name: str = Field(..., max_length=64)
    is_active: bool = True
    credentials: dict | None = None
    webhook_url: str | None = Field(None, max_length=256)

class UniversalChannelConfigurationCreate(UniversalChannelConfigurationBase):
    pass

class UniversalChannelConfigurationUpdate(BaseModel):
    is_active: bool | None = None
    credentials: dict | None = None

class UniversalChannelConfigurationResponse(UniversalChannelConfigurationBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Order Mapping
class UniversalOrderChannelMappingBase(BaseModel):
    channel_id: uuid.UUID
    sales_order_id: uuid.UUID | None = None
    external_order_id: str = Field(..., max_length=128)
    sync_status: str = Field("PENDING", max_length=32)
    raw_payload: dict | None = None

class UniversalOrderChannelMappingCreate(UniversalOrderChannelMappingBase):
    pass

class UniversalOrderChannelMappingResponse(UniversalOrderChannelMappingBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
