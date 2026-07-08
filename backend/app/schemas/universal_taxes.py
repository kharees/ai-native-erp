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

# Tax Configuration
class UniversalTaxConfigurationBase(BaseModel):
    name: str = Field(..., max_length=128)
    cgst_rate: float = Field(0.0, ge=0)
    sgst_rate: float = Field(0.0, ge=0)
    igst_rate: float = Field(0.0, ge=0)
    is_active: bool = True

class UniversalTaxConfigurationCreate(UniversalTaxConfigurationBase):
    pass

class UniversalTaxConfigurationUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)
    cgst_rate: float | None = Field(None, ge=0)
    sgst_rate: float | None = Field(None, ge=0)
    igst_rate: float | None = Field(None, ge=0)
    is_active: bool | None = None

class UniversalTaxConfigurationResponse(UniversalTaxConfigurationBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# HSN SAC
class UniversalHSNSACBase(BaseModel):
    code: str = Field(..., max_length=32)
    description: str | None = None
    code_type: str = Field("HSN", max_length=16)
    tax_config_id: uuid.UUID | None = None

class UniversalHSNSACCreate(UniversalHSNSACBase):
    pass

class UniversalHSNSACUpdate(BaseModel):
    code: str | None = Field(None, max_length=32)
    description: str | None = None
    code_type: str | None = Field(None, max_length=16)
    tax_config_id: uuid.UUID | None = None

class UniversalHSNSACResponse(UniversalHSNSACBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
