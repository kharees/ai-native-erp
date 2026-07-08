from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalBankAccount(Base):
    __tablename__ = 'universal_bank_accounts'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_name = mapped_column(String(length=128), nullable=False)
    account_number = mapped_column(String(length=64), nullable=False)
    account_type = mapped_column(String(length=32), nullable=False, server_default=text("'CURRENT'")) # CURRENT, SAVINGS
    ifsc_code = mapped_column(String(length=32), nullable=False)
    branch_name = mapped_column(String(length=128), nullable=True)
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'))
    current_balance = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalBankVoucher(Base):
    __tablename__ = 'universal_bank_vouchers'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_account_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_bank_accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    voucher_number = mapped_column(String(length=64), nullable=False, unique=True)
    voucher_type = mapped_column(String(length=32), nullable=False) # RECEIPT, PAYMENT, CONTRA
    amount = mapped_column(Numeric(15, 2), nullable=False)
    reference_number = mapped_column(String(length=128), nullable=True)
    remarks = mapped_column(Text(), nullable=True)
    transaction_date = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
