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

# Number Series
class UniversalNumberSeriesBase(BaseModel):
    entity_type: str = Field(..., max_length=64)
    branch_id: uuid.UUID | None = None
    financial_year: str | None = Field(None, max_length=16)
    prefix: str = Field(..., max_length=16)
    current_sequence: int = Field(0, ge=0)
    padding: int = Field(4, ge=1)
    is_active: bool = True

class UniversalNumberSeriesCreate(UniversalNumberSeriesBase):
    pass

class UniversalNumberSeriesUpdate(BaseModel):
    current_sequence: int | None = Field(None, ge=0)
    is_active: bool | None = None

class UniversalNumberSeriesResponse(UniversalNumberSeriesBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
