from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalAIBillingLog(Base):
    __tablename__ = 'universal_ai_billing_logs'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="CASCADE"), nullable=True, index=True)
    inference_type = mapped_column(String(length=64), nullable=False) # e.g., CREDIT_RISK, SMART_DRAFT, BUNDLE_SUGGESTION
    inference_payload = mapped_column(JSONB(astext_type=Text()), nullable=False)
    confidence_score = mapped_column(Numeric(5, 4), nullable=False)
    action_taken = mapped_column(String(length=32), nullable=False, server_default=text("'PENDING_REVIEW'")) # ACCEPTED, REJECTED, PENDING_REVIEW
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalAIFraudAlert(Base):
    __tablename__ = 'universal_ai_fraud_alerts'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="CASCADE"), nullable=True, index=True)
    invoice_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_tax_invoices.id", ondelete="CASCADE"), nullable=True, index=True)
    alert_type = mapped_column(String(length=64), nullable=False) # DUPLICATE_INVOICE, ABNORMAL_DISCOUNT, GHOST_CUSTOMER
    severity = mapped_column(String(length=32), nullable=False) # HIGH, MEDIUM, LOW
    alert_details = mapped_column(Text(), nullable=False)
    status = mapped_column(String(length=32), nullable=False, server_default=text("'OPEN'")) # OPEN, INVESTIGATING, RESOLVED, FALSE_POSITIVE
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
