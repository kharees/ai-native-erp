from __future__ import annotations

import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

# -----------------
# Batch Master
# -----------------
class UniversalBatchMasterBase(BaseModel):
    item_id: uuid.UUID
    batch_number: str = Field(..., max_length=128)
    mfg_date: date | None = None
    expiry_date: date | None = None
    shelf_life_days: int | None = None
    status: str = Field("active", max_length=32)
    cost_multiplier: float = Field(1.0, ge=0)

class UniversalBatchMasterCreate(UniversalBatchMasterBase):
    pass

class UniversalBatchMasterResponse(UniversalBatchMasterBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# -----------------
# Serial Master
# -----------------
class UniversalSerialMasterBase(BaseModel):
    item_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    serial_number: str = Field(..., max_length=128)
    status: str = Field("available", max_length=32)
    warehouse_id: uuid.UUID | None = None
    bin_id: uuid.UUID | None = None
    warranty_expiry: date | None = None

class UniversalSerialMasterCreate(UniversalSerialMasterBase):
    pass

class UniversalSerialMasterResponse(UniversalSerialMasterBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
