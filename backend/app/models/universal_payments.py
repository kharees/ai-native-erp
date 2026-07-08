from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalPaymentReceipt(Base):
    __tablename__ = 'universal_payment_receipts'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    bank_account_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_bank_accounts.id", ondelete="SET NULL"), nullable=True)
    receipt_number = mapped_column(String(length=64), nullable=False, unique=True)
    payment_mode = mapped_column(String(length=32), nullable=False) # CASH, BANK, UPI, CREDIT_CARD, DEBIT_CARD, CHEQUE, ONLINE
    reference_number = mapped_column(String(length=128), nullable=True)
    amount_received = mapped_column(Numeric(15, 2), nullable=False)
    unallocated_amount = mapped_column(Numeric(15, 2), nullable=False)
    payment_date = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    status = mapped_column(String(length=32), nullable=False, server_default=text("'CLEARED'")) # CLEARED, PENDING, BOUNCED
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalPaymentAllocation(Base):
    __tablename__ = 'universal_payment_allocations'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_payment_receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_tax_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    allocated_amount = mapped_column(Numeric(15, 2), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalRefund(Base):
    __tablename__ = 'universal_refunds'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    receipt_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_payment_receipts.id", ondelete="SET NULL"), nullable=True)
    credit_note_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_credit_notes.id", ondelete="SET NULL"), nullable=True)
    bank_account_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_bank_accounts.id", ondelete="SET NULL"), nullable=True)
    refund_number = mapped_column(String(length=64), nullable=False, unique=True)
    payment_mode = mapped_column(String(length=32), nullable=False)
    reference_number = mapped_column(String(length=128), nullable=True)
    amount_refunded = mapped_column(Numeric(15, 2), nullable=False)
    refund_date = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    status = mapped_column(String(length=32), nullable=False, server_default=text("'CLEARED'"))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalCustomerWallet(Base):
    __tablename__ = 'universal_customer_wallets'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="CASCADE"), nullable=False, unique=True)
    balance = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
