import enum
import uuid
from sqlalchemy import *
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

# --- Fixed Assets ---
class DepreciationMethod(str, enum.Enum):
    SLM = "SLM" # Straight Line Method
    WDV = "WDV" # Written Down Value
    CUSTOM = "CUSTOM"

class FixedAssetCategory(Base):
    __tablename__ = 'finance_asset_categories'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(128), nullable=False)
    depreciation_method = mapped_column(Enum(DepreciationMethod, name='finance_depreciation_method'), nullable=False, default=DepreciationMethod.SLM)
    default_depreciation_rate = mapped_column(Numeric(5, 2), nullable=False, default=0.00) # e.g. 10.00 for 10%
    asset_account_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_accounts.id", ondelete="RESTRICT"), nullable=True)
    depreciation_account_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_accounts.id", ondelete="RESTRICT"), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class FixedAsset(Base):
    __tablename__ = 'finance_fixed_assets'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_asset_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    asset_code = mapped_column(String(100), nullable=False)
    name = mapped_column(String(255), nullable=False)
    acquisition_date = mapped_column(DateTime(timezone=True), nullable=False)
    acquisition_cost = mapped_column(Numeric(15, 2), nullable=False)
    salvage_value = mapped_column(Numeric(15, 2), nullable=False, default=0.00)
    useful_life_years = mapped_column(Integer, nullable=False, default=1)
    current_value = mapped_column(Numeric(15, 2), nullable=False)
    depreciation_method = mapped_column(Enum(DepreciationMethod, name='finance_depreciation_method'), nullable=False)
    depreciation_rate = mapped_column(Numeric(5, 2), nullable=False)
    status = mapped_column(String(50), default="ACTIVE", nullable=False) # ACTIVE, DISPOSED, MAINTENANCE
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (UniqueConstraint('tenant_id', 'asset_code', name='uq_tenant_asset_code'),)

class AssetDepreciationLog(Base):
    __tablename__ = 'finance_asset_depreciation_logs'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_fixed_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    depreciation_date = mapped_column(DateTime(timezone=True), nullable=False)
    depreciation_amount = mapped_column(Numeric(15, 2), nullable=False)
    voucher_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_journal_vouchers.id", ondelete="SET NULL"), nullable=True) # Linked JE
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# --- Cost & Profit Centers ---
class CostCenter(Base):
    __tablename__ = 'finance_cost_centers'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    code = mapped_column(String(100), nullable=False)
    name = mapped_column(String(255), nullable=False)
    department = mapped_column(String(128), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ProfitCenter(Base):
    __tablename__ = 'finance_profit_centers'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    code = mapped_column(String(100), nullable=False)
    name = mapped_column(String(255), nullable=False)
    business_unit = mapped_column(String(128), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# --- Budgeting & Forecasting ---
class Budget(Base):
    __tablename__ = 'finance_budgets'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(255), nullable=False)
    fiscal_year = mapped_column(String(20), nullable=False)
    period_type = mapped_column(String(50), default="ANNUAL", nullable=False) # ANNUAL, QUARTERLY, MONTHLY
    status = mapped_column(String(50), default="DRAFT", nullable=False) # DRAFT, APPROVED, ACTIVE, CLOSED
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class BudgetLine(Base):
    __tablename__ = 'finance_budget_lines'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    budget_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_budgets.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_accounts.id", ondelete="CASCADE"), nullable=False)
    allocated_amount = mapped_column(Numeric(15, 2), nullable=False, default=0.00)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Forecast(Base):
    __tablename__ = 'finance_forecasts'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(255), nullable=False)
    target_period = mapped_column(String(50), nullable=False) # e.g. "Q3-2026"
    forecast_type = mapped_column(String(50), nullable=False) # REVENUE, EXPENSE, CASH_FLOW
    predicted_amount = mapped_column(Numeric(15, 2), nullable=False, default=0.00)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
