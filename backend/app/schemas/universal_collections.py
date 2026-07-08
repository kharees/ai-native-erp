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

class CollectionStatusResponse(BaseModel):
    customer_id: uuid.UUID
    customer_name: str
    credit_limit: float
    credit_days: int
    total_outstanding: float
    overdue_amount: float
    isOnCreditHold: bool

class AgingBucketResponse(BaseModel):
    bucket_0_30: float
    bucket_31_60: float
    bucket_61_90: float
    bucket_90_plus: float
    total: float
