"""
app/schemas/sales_fulfillment.py
===================================
Request/response shapes specific to app/services/sales_fulfillment.py --
composite operations (quotation + stock reservation) that don't map onto
any single existing CRUD schema.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QuotationStockCheckItem(BaseModel):
    item_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    # Numeric(15, 2) in the DB (see app/models/universal_sales.py) --
    # Decimal end to end, matching app/schemas/universal_invoices.py's
    # money fields, since this feeds straight into an invoice via
    # convert_quotation_to_invoice.
    unit_price: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2)


class QuotationWithStockCheckCreate(BaseModel):
    customer_id: uuid.UUID
    quotation_number: str = Field(..., max_length=64)
    warehouse_id: uuid.UUID
    valid_until: datetime | None = None
    reservation_expires_at: datetime
    items: list[QuotationStockCheckItem]


class StockShortfallItem(BaseModel):
    item_id: str
    requested: float
    available: float


class StockReservationResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    quotation_id: uuid.UUID
    quantity: float
    expires_at: datetime
    model_config = ConfigDict(from_attributes=True)
