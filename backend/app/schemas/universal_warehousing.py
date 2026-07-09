from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

# -----------------
# Warehouses
# -----------------
class UniversalWarehouseBase(BaseModel):
    branch_id: uuid.UUID | None = None
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    type: str = Field("main", max_length=64)
    status: str = Field("active", max_length=32)
    manager_id: uuid.UUID | None = None
    capacity_sqft: float = Field(0.0, ge=0)
    is_active: bool = True

class UniversalWarehouseCreate(UniversalWarehouseBase):
    pass

class UniversalWarehouseUpdate(BaseModel):
    branch_id: uuid.UUID | None = None
    code: str | None = Field(None, max_length=64)
    name: str | None = Field(None, max_length=255)
    type: str | None = Field(None, max_length=64)
    status: str | None = Field(None, max_length=32)
    manager_id: uuid.UUID | None = None
    capacity_sqft: float | None = Field(None, ge=0)
    is_active: bool | None = None

class UniversalWarehouseResponse(UniversalWarehouseBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# -----------------
# Warehouse Zones
# -----------------
class UniversalWarehouseZoneBase(BaseModel):
    warehouse_id: uuid.UUID
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    type: str | None = Field(None, max_length=64)
    is_active: bool = True

class UniversalWarehouseZoneCreate(UniversalWarehouseZoneBase):
    pass

class UniversalWarehouseZoneUpdate(BaseModel):
    code: str | None = Field(None, max_length=64)
    name: str | None = Field(None, max_length=255)
    type: str | None = Field(None, max_length=64)
    is_active: bool | None = None

class UniversalWarehouseZoneResponse(UniversalWarehouseZoneBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# -----------------
# Warehouse Bins
# -----------------
class UniversalWarehouseBinBase(BaseModel):
    warehouse_id: uuid.UUID
    zone_id: uuid.UUID | None = None
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    aisle: str | None = Field(None, max_length=64)
    rack: str | None = Field(None, max_length=64)
    shelf: str | None = Field(None, max_length=64)
    max_weight: float = Field(0.0, ge=0)
    max_volume: float = Field(0.0, ge=0)
    metadata_fields: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    is_active: bool = True

class UniversalWarehouseBinCreate(UniversalWarehouseBinBase):
    pass

class UniversalWarehouseBinUpdate(BaseModel):
    zone_id: uuid.UUID | None = None
    code: str | None = Field(None, max_length=64)
    name: str | None = Field(None, max_length=255)
    aisle: str | None = Field(None, max_length=64)
    rack: str | None = Field(None, max_length=64)
    shelf: str | None = Field(None, max_length=64)
    max_weight: float | None = Field(None, ge=0)
    max_volume: float | None = Field(None, ge=0)
    metadata_fields: dict[str, Any] | None = Field(None, alias="metadata")
    is_active: bool | None = None

class UniversalWarehouseBinResponse(UniversalWarehouseBinBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# -----------------
# Stock Engine
# -----------------
class StockMovementRequest(BaseModel):
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    bin_id: uuid.UUID | None = None
    batch_id: uuid.UUID | None = None
    serial_numbers: list[str] | None = None
    
    transaction_type: str = Field(..., max_length=32)
    reference_type: str = Field(..., max_length=64)
    reference_id: str | None = Field(None, max_length=128)
    quantity: float = Field(..., gt=0)
    metadata_fields: dict[str, Any] = Field(default_factory=dict, alias="metadata")

class StockBalanceResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    bin_id: uuid.UUID | None = None
    quantity_on_hand: float
    quantity_reserved: float
    quantity_allocated: float
    last_transaction_at: datetime
    model_config = ConfigDict(from_attributes=True)

class StockTransactionResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    bin_id: uuid.UUID | None = None
    transaction_type: str
    reference_type: str
    reference_id: str | None
    quantity: float
    metadata_fields: dict[str, Any] = Field(..., alias="metadata")
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
