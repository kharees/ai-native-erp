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

# -----------------
# Category Schemas
# -----------------
class UniversalCategoryBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    is_active: bool = True

class UniversalCategoryCreate(UniversalCategoryBase):
    pass

class UniversalCategoryUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    is_active: bool | None = None

class UniversalCategoryResponse(UniversalCategoryBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# -----------------
# Brand Schemas
# -----------------
class UniversalBrandBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    website: str | None = Field(None, max_length=255)
    logo_url: str | None = Field(None, max_length=1024)
    is_active: bool = True

class UniversalBrandCreate(UniversalBrandBase):
    pass

class UniversalBrandUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    website: str | None = Field(None, max_length=255)
    logo_url: str | None = Field(None, max_length=1024)
    is_active: bool | None = None

class UniversalBrandResponse(UniversalBrandBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# -----------------
# UOM Schemas
# -----------------
class UniversalUOMBase(BaseModel):
    name: str = Field(..., max_length=128)
    abbreviation: str = Field(..., max_length=32)
    base_uom_id: uuid.UUID | None = None
    conversion_factor: float = 1.0
    decimal_precision: int = Field(0, ge=0)
    is_active: bool = True

class UniversalUOMCreate(UniversalUOMBase):
    pass

class UniversalUOMUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)
    abbreviation: str | None = Field(None, max_length=32)
    base_uom_id: uuid.UUID | None = None
    conversion_factor: float | None = None
    decimal_precision: int | None = Field(None, ge=0)
    is_active: bool | None = None

class UniversalUOMResponse(UniversalUOMBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# -----------------
# Item Master Schemas
# -----------------
class UniversalItemMasterBase(BaseModel):
    item_code: str = Field(..., max_length=64)
    sku: str = Field(..., max_length=64)
    barcode: str | None = Field(None, max_length=128)
    qr_code: str | None = Field(None, max_length=128)
    name: str = Field(..., max_length=255)
    short_name: str | None = Field(None, max_length=128)
    description: str | None = None
    status: str = Field("draft", max_length=32)
    is_active: bool = True
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    uom_id: uuid.UUID | None = None
    images: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    notes: str | None = None
    variants: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)

class UniversalItemMasterCreate(UniversalItemMasterBase):
    pass

class UniversalItemMasterUpdate(BaseModel):
    item_code: str | None = Field(None, max_length=64)
    sku: str | None = Field(None, max_length=64)
    barcode: str | None = Field(None, max_length=128)
    qr_code: str | None = Field(None, max_length=128)
    name: str | None = Field(None, max_length=255)
    short_name: str | None = Field(None, max_length=128)
    description: str | None = None
    status: str | None = Field(None, max_length=32)
    is_active: bool | None = None
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    uom_id: uuid.UUID | None = None
    images: list[str] | None = None
    documents: list[str] | None = None
    notes: str | None = None
    variants: dict[str, Any] | None = None
    attributes: dict[str, Any] | None = None

class UniversalItemMasterResponse(UniversalItemMasterBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
