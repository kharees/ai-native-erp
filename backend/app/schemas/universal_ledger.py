from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class UniversalInventoryLedgerResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    bin_id: uuid.UUID | None = None
    transaction_id: uuid.UUID | None = None
    
    quantity_before: float
    movement_quantity: float
    quantity_after: float
    
    unit_cost: float
    total_cost: float
    
    reference_type: str
    reference_id: str | None = None
    user_id: uuid.UUID | None = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
