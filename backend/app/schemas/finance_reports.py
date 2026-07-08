from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from decimal import Decimal

# --- Trial Balance Schemas ---
class TrialBalanceLine(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    opening_debit: Decimal = Decimal("0.00")
    opening_credit: Decimal = Decimal("0.00")
    period_debit: Decimal = Decimal("0.00")
    period_credit: Decimal = Decimal("0.00")
    closing_debit: Decimal = Decimal("0.00")
    closing_credit: Decimal = Decimal("0.00")

class TrialBalanceReport(BaseModel):
    tenant_id: str
    start_date: Optional[date]
    end_date: Optional[date]
    lines: List[TrialBalanceLine]
    total_debit: Decimal
    total_credit: Decimal

# --- Profit & Loss Schemas ---
class PLCategoryLine(BaseModel):
    category_name: str
    amount: Decimal
    accounts: List[dict] # {account_name, amount}

class ProfitAndLossReport(BaseModel):
    tenant_id: str
    start_date: Optional[date]
    end_date: Optional[date]
    revenue: List[PLCategoryLine]
    cogs: List[PLCategoryLine]
    gross_profit: Decimal
    operating_expenses: List[PLCategoryLine]
    operating_profit: Decimal
    net_profit: Decimal

# --- Balance Sheet Schemas ---
class BSCategoryLine(BaseModel):
    category_name: str
    amount: Decimal
    accounts: List[dict]

class BalanceSheetReport(BaseModel):
    tenant_id: str
    as_of_date: date
    assets: List[BSCategoryLine]
    total_assets: Decimal
    liabilities: List[BSCategoryLine]
    total_liabilities: Decimal
    equity: List[BSCategoryLine]
    total_equity: Decimal
    # Equation: total_assets = total_liabilities + total_equity

# --- Cash Flow Schemas ---
class CashFlowCategoryLine(BaseModel):
    description: str
    amount: Decimal

class CashFlowReport(BaseModel):
    tenant_id: str
    start_date: Optional[date]
    end_date: Optional[date]
    operating_activities: List[CashFlowCategoryLine]
    net_operating_cash: Decimal
    investing_activities: List[CashFlowCategoryLine]
    net_investing_cash: Decimal
    financing_activities: List[CashFlowCategoryLine]
    net_financing_cash: Decimal
    net_cash_increase: Decimal
    opening_cash_balance: Decimal
    closing_cash_balance: Decimal
