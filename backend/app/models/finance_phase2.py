import enum
import uuid
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

# --- Accounts Receivable ---
class ARLedger(Base):
    __tablename__ = 'finance_ar_ledger'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="CASCADE"), nullable=False, index=True)
    outstanding_amount = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    credit_limit = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    is_bad_debt = mapped_column(Boolean, default=False, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (UniqueConstraint('tenant_id', 'customer_id', name='uq_tenant_customer_ar'),)

class ARCollection(Base):
    __tablename__ = 'finance_ar_collections'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="CASCADE"), nullable=False, index=True)
    status = mapped_column(String(50), default="PROMISED_TO_PAY", nullable=False)
    notes = mapped_column(Text, nullable=True)
    follow_up_date = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ARReceipt(Base):
    __tablename__ = 'finance_ar_receipts'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_number = mapped_column(String(100), nullable=False)
    amount = mapped_column(Numeric(15, 2), nullable=False)
    unallocated_amount = mapped_column(Numeric(15, 2), nullable=False)
    payment_mode = mapped_column(String(50), nullable=False)
    reference = mapped_column(String(100), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (UniqueConstraint('tenant_id', 'receipt_number', name='uq_tenant_ar_receipt_num'),)

# --- Accounts Payable ---
class APVendor(Base):
    __tablename__ = 'finance_ap_vendors'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(255), nullable=False)
    email = mapped_column(String(320), nullable=True)
    phone = mapped_column(String(32), nullable=True)
    tax_number = mapped_column(String(50), nullable=True)
    outstanding_amount = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class APBill(Base):
    __tablename__ = 'finance_ap_bills'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_ap_vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    bill_number = mapped_column(String(100), nullable=False)
    amount = mapped_column(Numeric(15, 2), nullable=False)
    due_date = mapped_column(DateTime(timezone=True), nullable=False)
    status = mapped_column(String(50), default="UNPAID", nullable=False) # UNPAID, PARTIAL, PAID
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (UniqueConstraint('tenant_id', 'bill_number', 'vendor_id', name='uq_tenant_vendor_bill_num'),)

class APPayment(Base):
    __tablename__ = 'finance_ap_payments'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_ap_vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_number = mapped_column(String(100), nullable=False)
    amount = mapped_column(Numeric(15, 2), nullable=False)
    payment_mode = mapped_column(String(50), nullable=False, default="BANK_TRANSFER")
    reference = mapped_column(String(100), nullable=True)
    unallocated_amount = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    status = mapped_column(String(50), default="PENDING_APPROVAL", nullable=False)
    approved_by = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (UniqueConstraint('tenant_id', 'payment_number', name='uq_tenant_ap_payment_num'),)

# --- Banking & Cash ---
class BankReconciliation(Base):
    __tablename__ = 'finance_bank_reconciliations'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_account_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    statement_date = mapped_column(DateTime(timezone=True), nullable=False)
    statement_balance = mapped_column(Numeric(15, 2), nullable=False)
    system_balance = mapped_column(Numeric(15, 2), nullable=False)
    status = mapped_column(String(50), default="PENDING", nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class CashAccount(Base):
    __tablename__ = 'finance_cash_accounts'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(128), nullable=False)
    is_petty_cash = mapped_column(Boolean, default=False, nullable=False)
    balance = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

# --- Expenses ---
class ExpenseCategory(Base):
    __tablename__ = 'finance_expense_categories'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(128), nullable=False)
    description = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ExpenseClaim(Base):
    __tablename__ = 'finance_expense_claims'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_expense_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = mapped_column(Numeric(15, 2), nullable=False)
    status = mapped_column(String(50), default="SUBMITTED", nullable=False) # SUBMITTED, APPROVED, REJECTED, PAID
    approved_by = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    description = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
