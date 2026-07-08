import enum
import uuid
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

class AccountCategory(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"

class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"

class JournalStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    POSTED = "posted"
    REVERSED = "reversed"

class AccountGroup(Base):
    __tablename__ = 'finance_account_groups'
    
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(255), nullable=False)
    code = mapped_column(String(50), nullable=True)
    parent_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_account_groups.id", ondelete="SET NULL"), nullable=True)
    category = mapped_column(Enum(AccountCategory, name='finance_account_category'), nullable=False)
    description = mapped_column(Text, nullable=True)
    is_active = mapped_column(Boolean, default=True, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    parent = relationship("AccountGroup", remote_side=[id], back_populates="children")
    children = relationship("AccountGroup", back_populates="parent")
    accounts = relationship("Account", back_populates="group")


class Account(Base):
    __tablename__ = 'finance_accounts'
    
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_account_groups.id", ondelete="RESTRICT"), nullable=False, index=True)
    account_code = mapped_column(String(50), nullable=False)
    name = mapped_column(String(255), nullable=False)
    status = mapped_column(Enum(AccountStatus, name='finance_account_status'), default=AccountStatus.ACTIVE, nullable=False)
    currency = mapped_column(String(3), default='USD', nullable=False)
    is_reconciliation_account = mapped_column(Boolean, default=False, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    group = relationship("AccountGroup", back_populates="accounts")
    # Enforce unique account code per tenant
    __table_args__ = (
        UniqueConstraint('tenant_id', 'account_code', name='uq_tenant_account_code'),
    )


class JournalVoucher(Base):
    __tablename__ = 'finance_journal_vouchers'
    
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    voucher_number = mapped_column(String(100), nullable=False)
    reference = mapped_column(String(255), nullable=True)
    entry_date = mapped_column(DateTime(timezone=True), nullable=False)
    status = mapped_column(Enum(JournalStatus, name='finance_journal_status'), default=JournalStatus.DRAFT, nullable=False)
    description = mapped_column(Text, nullable=True)
    
    total_debit = mapped_column(Numeric(precision=15, scale=2), default=0.00, nullable=False)
    total_credit = mapped_column(Numeric(precision=15, scale=2), default=0.00, nullable=False)
    
    source_document_type = mapped_column(String(100), nullable=True) # e.g., 'sales_invoice', 'vendor_payment'
    source_document_id = mapped_column(String(100), nullable=True)
    
    created_by = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    approved_by = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    lines = relationship("JournalEntryLine", back_populates="voucher", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'voucher_number', name='uq_tenant_voucher_number'),
    )


class JournalEntryLine(Base):
    __tablename__ = 'finance_journal_entry_lines'
    
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    voucher_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_journal_vouchers.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = mapped_column(UUID(as_uuid=True), ForeignKey("finance_accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    debit = mapped_column(Numeric(precision=15, scale=2), default=0.00, nullable=False)
    credit = mapped_column(Numeric(precision=15, scale=2), default=0.00, nullable=False)
    
    description = mapped_column(String(255), nullable=True)
    cost_center_id = mapped_column(UUID(as_uuid=True), nullable=True) # Could be foreign key later
    profit_center_id = mapped_column(UUID(as_uuid=True), nullable=True)
    
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    voucher = relationship("JournalVoucher", back_populates="lines")
    account = relationship("Account")
