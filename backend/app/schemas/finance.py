"""
app/schemas/finance.py
======================
Pydantic validation schemas for the AI Copilot Ledger & Finance Engine.

Validates income and expense data maps before pushing to the 
TenantFinanceLedger repository model.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.finance import TransactionType


class FinanceLedgerBase(BaseModel):
    """
    Base data parameters capturing core financial flows and AI metadata.
    """
    transaction_type: TransactionType
    category: str = Field(..., max_length=128, description="Financial category mapping")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Strictly positive financial value")
    currency: str = Field("INR", max_length=3)
    description: Optional[str] = None
    
    # Store AI generated trend flags, budget markers, and cost-saving indices.
    metadata_insights: dict[str, Any] = Field(default_factory=dict)


class FinanceLedgerCreate(FinanceLedgerBase):
    """
    Configuration parameters used when recording a new ledger transaction.
    """
    # entry_date is omitted to strictly rely on database-generated func.now() UTC time,
    # ensuring financial auditing consistency.
    pass


class FinanceLedgerResponse(FinanceLedgerBase):
    """
    Response configurations pushing safe, tracked values out to the UI/client layer.
    """
    id: UUID
    tenant_id: UUID
    entry_date: datetime
    
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinanceSummaryResponse(BaseModel):
    """
    Aggregation response schema for the get_finance_summary endpoint.
    """
    tenant_id: UUID
    total_income: Decimal = Field(..., decimal_places=2)
    total_expense: Decimal = Field(..., decimal_places=2)
    net_balance: Decimal = Field(..., decimal_places=2)
    currency: str = Field("INR")
