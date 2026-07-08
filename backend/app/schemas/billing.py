"""
app/schemas/billing.py
======================
Pydantic validation schemas for the Omnichannel Billing & Invoice Engine.

Implements strict validation mapping for the TenantBillingInvoice database models,
ensuring data correctness at the edge before it reaches the async database layer.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.billing import PaymentMode, PaymentStatus


class BillingItemSnapshot(BaseModel):
    """
    Validation schema for elements inside the items_snapshot JSONB array.
    Ensures every line item contains valid financial fields before DB ingestion.
    """
    sku: str = Field(..., max_length=64, description="Stock Keeping Unit identifier")
    name: str = Field(..., max_length=255, description="Item display name")
    quantity: int = Field(..., gt=0, description="Quantity sold")
    unit_price: Decimal = Field(..., ge=0, decimal_places=2, description="Price per unit")
    line_total: Decimal = Field(..., ge=0, decimal_places=2, description="quantity * unit_price")
    currency: str = Field("INR", max_length=3, description="ISO 4217 currency code")
    tax_rate_pct: Decimal = Field(..., ge=0, decimal_places=4, description="Tax rate percentage")
    tax_amount: Decimal = Field(..., ge=0, decimal_places=2, description="Calculated tax amount for this line")
    discount_pct: Decimal = Field(0.0, ge=0, decimal_places=4, description="Discount percentage applied")
    attributes: Optional[dict[str, Any]] = Field(default_factory=dict, description="Immutable snapshot of product attributes")


class BillingInvoiceBase(BaseModel):
    """
    Core data attributes mirroring the backend TenantBillingInvoice model.
    """
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=320)
    customer_phone: Optional[str] = Field(None, max_length=32)
    customer_gstin: Optional[str] = Field(None, max_length=15)
    billing_address: Optional[str] = None
    
    currency: str = Field("INR", max_length=3)
    subtotal: Decimal = Field(..., ge=0, decimal_places=2)
    tax_amount: Decimal = Field(..., ge=0, decimal_places=2)
    total_amount: Decimal = Field(..., ge=0, decimal_places=2)
    discount_amount: Decimal = Field(0, ge=0, decimal_places=2)
    tax_rate_pct: Optional[Decimal] = Field(None, ge=0)
    gstin_seller: Optional[str] = Field(None, max_length=15)
    
    payment_mode: Optional[PaymentMode] = None
    
    items_snapshot: List[BillingItemSnapshot] = Field(default_factory=list, min_length=1)
    notes: Optional[str] = None
    invoice_metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class BillingInvoiceCreate(BillingInvoiceBase):
    """
    Configuration parameters layer for creating a new invoice.
    Excludes server-generated fields like id, tenant_id, and invoice_number.
    """
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    payment_reference: Optional[str] = Field(None, max_length=128)
    due_date: Optional[datetime] = None


class BillingInvoiceResponse(BillingInvoiceBase):
    """
    Tracking model metrics arrays returned to the client.
    Includes the unique invoice tracking code and internal metadata.
    """
    id: UUID
    tenant_id: UUID
    invoice_number: str
    payment_status: PaymentStatus
    payment_reference: Optional[str]
    paid_at: Optional[datetime]
    due_date: Optional[datetime]
    
    is_active: bool
    invoice_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
