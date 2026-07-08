import uuid
from pydantic import BaseModel
from typing import List

class StockValuationSummary(BaseModel):
    total_quantity: float
    total_value: float
    warehouse_count: int
    item_count: int

class ABCAnalysisItem(BaseModel):
    item_id: uuid.UUID
    item_code: str | None = None
    item_name: str | None = None
    total_value_consumed: float
    cumulative_percentage: float
    classification: str # 'A', 'B', 'C'

class AgingReportItem(BaseModel):
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_on_hand: float
    days_since_last_movement: int
    aging_bucket: str # '0-30', '31-90', '91-180', '180+'

class KPIReport(BaseModel):
    total_inventory_value: float
    dead_stock_value: float
    active_batches: int
    items_near_expiry: int
