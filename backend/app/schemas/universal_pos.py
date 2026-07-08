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

# POS Session
class UniversalPOSSessionBase(BaseModel):
    user_id: uuid.UUID
    session_status: str = Field("OPEN", max_length=32)
    opening_balance: float = Field(0.0, ge=0)
    closing_balance: float | None = Field(None, ge=0)

class UniversalPOSSessionCreate(UniversalPOSSessionBase):
    pass

class UniversalPOSSessionUpdate(BaseModel):
    session_status: str | None = Field(None, max_length=32)
    closing_balance: float | None = Field(None, ge=0)

class UniversalPOSSessionResponse(UniversalPOSSessionBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    opened_at: datetime
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# POS Hold Bill
class UniversalPOSHoldBillBase(BaseModel):
    session_id: uuid.UUID
    reference_name: str | None = Field(None, max_length=128)
    cart_data: dict = Field(...)

class UniversalPOSHoldBillCreate(UniversalPOSHoldBillBase):
    pass

class UniversalPOSHoldBillUpdate(BaseModel):
    cart_data: dict | None = None

class UniversalPOSHoldBillResponse(UniversalPOSHoldBillBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
