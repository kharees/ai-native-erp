from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- TenantBillingInvoice ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantBillingInvoice(Base):
    __tablename__ = 'tenant_billing_invoices'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    invoice_number = mapped_column(String(length=64), nullable=False, unique=True, )
    customer_name = mapped_column(String(length=255), nullable=True, )
    customer_email = mapped_column(String(length=320), nullable=True, )
    customer_phone = mapped_column(String(length=32), nullable=True, )
    customer_gstin = mapped_column(String(length=15), nullable=True, )
    billing_address = mapped_column(Text(), nullable=True, )
    currency = mapped_column(String(length=3), nullable=False, server_default=text("'INR'"), )
    subtotal = mapped_column(Numeric(precision=10, scale=2), nullable=False, server_default=text('0'), )
    tax_amount = mapped_column(Numeric(precision=10, scale=2), nullable=False, server_default=text('0'), )
    total_amount = mapped_column(Numeric(precision=10, scale=2), nullable=False, server_default=text('0'), )
    discount_amount = mapped_column(Numeric(precision=10, scale=2), nullable=False, server_default=text('0'), )
    tax_rate_pct = mapped_column(Numeric(precision=6, scale=4), nullable=True, )
    gstin_seller = mapped_column(String(length=15), nullable=True, )
    payment_status = mapped_column(Enum('PENDING', 'PAID', 'OVERDUE', 'CANCELLED', 'FAILED', 'REFUNDED', 'PARTIAL', name='billing_payment_status', schema='public'), nullable=False, server_default=text("'PENDING'"), )
    payment_mode = mapped_column(Enum('UPI', 'CASH', 'CARD', 'ONLINE', 'CHEQUE', 'BANK_TRANSFER', 'WALLET', 'EMI', 'CREDIT', 'OTHER', name='billing_payment_mode', schema='public'), nullable=True, )
    payment_reference = mapped_column(String(length=128), nullable=True, )
    paid_at = mapped_column(DateTime(timezone=True), nullable=True, )
    due_date = mapped_column(DateTime(timezone=True), nullable=True, )
    items_snapshot = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'[]'::jsonb"), )
    notes = mapped_column(Text(), nullable=True, )
    invoice_metadata = mapped_column(JSONB(astext_type=Text()), nullable=True, server_default=text("'{}'::jsonb"), )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    invoice_version = mapped_column(Numeric(precision=6, scale=0), nullable=False, server_default=text('1'), )
    created_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    updated_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )

from enum import Enum
class PaymentMode(str, Enum):
    CREDIT_CARD = 'credit_card'
    BANK_TRANSFER = 'bank_transfer'
    CASH = 'cash'
    PAYPAL = 'paypal'

class PaymentStatus(str, Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'
