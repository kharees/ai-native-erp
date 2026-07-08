from __future__ import annotations
import uuid
from datetime import date
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

class SalesTrendPoint(BaseModel):
    date_label: str # "2023-10-01", "2023-10"
    total_sales: float
    order_count: int

class SalesSummaryResponse(BaseModel):
    total_revenue: float
    total_orders: int
    average_order_value: float
    trends: list[SalesTrendPoint]

class AnalyticsLeaderboardItem(BaseModel):
    name: str
    value: float
    count: int

class AnalyticsLeaderboardResponse(BaseModel):
    top_products: list[AnalyticsLeaderboardItem]
    top_customers: list[AnalyticsLeaderboardItem]
    top_channels: list[AnalyticsLeaderboardItem]

class FinancialSummaryResponse(BaseModel):
    total_outstanding: float
    total_collected: float
    total_tax_collected: float
    aging_buckets: dict[str, float]
