from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal

# --- Fixed Assets ---
class FixedAssetCategoryBase(BaseModel):
    name: str
    depreciation_method: str = "SLM"
    default_depreciation_rate: Decimal
    asset_account_id: Optional[UUID] = None
    depreciation_account_id: Optional[UUID] = None

class FixedAssetCategoryCreate(FixedAssetCategoryBase):
    tenant_id: UUID

class FixedAssetCategoryOut(FixedAssetCategoryBase):
    id: UUID
    tenant_id: UUID
    model_config = ConfigDict(from_attributes=True)

class FixedAssetBase(BaseModel):
    category_id: UUID
    asset_code: str
    name: str
    acquisition_date: datetime
    acquisition_cost: Decimal
    salvage_value: Decimal = Decimal("0.00")
    useful_life_years: int = 1
    current_value: Decimal
    depreciation_method: str
    depreciation_rate: Decimal
    status: str = "ACTIVE"

class FixedAssetCreate(FixedAssetBase):
    tenant_id: UUID

class FixedAssetOut(FixedAssetBase):
    id: UUID
    tenant_id: UUID
    model_config = ConfigDict(from_attributes=True)

class AssetDepreciationLogBase(BaseModel):
    asset_id: UUID
    depreciation_date: datetime
    depreciation_amount: Decimal
    voucher_id: Optional[UUID] = None

class AssetDepreciationLogOut(AssetDepreciationLogBase):
    id: UUID
    tenant_id: UUID
    model_config = ConfigDict(from_attributes=True)

# --- Cost & Profit Centers ---
class CostCenterBase(BaseModel):
    code: str
    name: str
    department: Optional[str] = None

class CostCenterCreate(CostCenterBase):
    tenant_id: UUID

class CostCenterOut(CostCenterBase):
    id: UUID
    tenant_id: UUID
    model_config = ConfigDict(from_attributes=True)

class ProfitCenterBase(BaseModel):
    code: str
    name: str
    business_unit: Optional[str] = None

class ProfitCenterCreate(ProfitCenterBase):
    tenant_id: UUID

class ProfitCenterOut(ProfitCenterBase):
    id: UUID
    tenant_id: UUID
    model_config = ConfigDict(from_attributes=True)

# --- Budgeting & Forecasting ---
class BudgetLineBase(BaseModel):
    account_id: UUID
    allocated_amount: Decimal

class BudgetBase(BaseModel):
    name: str
    fiscal_year: str
    period_type: str = "ANNUAL"
    status: str = "DRAFT"

class BudgetCreate(BudgetBase):
    tenant_id: UUID
    lines: List[BudgetLineBase] = []

class BudgetOut(BudgetBase):
    id: UUID
    tenant_id: UUID
    model_config = ConfigDict(from_attributes=True)

class ForecastBase(BaseModel):
    name: str
    target_period: str
    forecast_type: str
    predicted_amount: Decimal

class ForecastCreate(ForecastBase):
    tenant_id: UUID

class ForecastOut(ForecastBase):
    id: UUID
    tenant_id: UUID
    model_config = ConfigDict(from_attributes=True)
