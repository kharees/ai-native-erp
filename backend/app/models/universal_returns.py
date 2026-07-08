from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalCreditNote(Base):
    __tablename__ = 'universal_credit_notes'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    tax_invoice_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_tax_invoices.id", ondelete="SET NULL"), nullable=True)
    note_number = mapped_column(String(length=64), nullable=False, unique=True)
    reason = mapped_column(Text(), nullable=True)
    status = mapped_column(String(length=32), nullable=False, server_default=text("'DRAFT'"))
    total_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalCreditNoteItem(Base):
    __tablename__ = 'universal_credit_note_items'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    note_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_credit_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_item_master.id", ondelete="RESTRICT"), nullable=False)
    quantity = mapped_column(Numeric(15, 4), nullable=False)
    unit_price = mapped_column(Numeric(15, 2), nullable=False)
    line_total = mapped_column(Numeric(15, 2), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalDebitNote(Base):
    __tablename__ = 'universal_debit_notes'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    tax_invoice_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_tax_invoices.id", ondelete="SET NULL"), nullable=True)
    note_number = mapped_column(String(length=64), nullable=False, unique=True)
    reason = mapped_column(Text(), nullable=True)
    status = mapped_column(String(length=32), nullable=False, server_default=text("'DRAFT'"))
    total_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalDebitNoteItem(Base):
    __tablename__ = 'universal_debit_note_items'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    note_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_debit_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_item_master.id", ondelete="RESTRICT"), nullable=False)
    quantity = mapped_column(Numeric(15, 4), nullable=False)
    unit_price = mapped_column(Numeric(15, 2), nullable=False)
    line_total = mapped_column(Numeric(15, 2), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalSalesReturn(Base):
    __tablename__ = 'universal_sales_returns'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    delivery_challan_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_delivery_challans.id", ondelete="SET NULL"), nullable=True)
    return_number = mapped_column(String(length=64), nullable=False, unique=True)
    reason = mapped_column(Text(), nullable=True)
    status = mapped_column(String(length=32), nullable=False, server_default=text("'PENDING'"))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalSalesReturnItem(Base):
    __tablename__ = 'universal_sales_return_items'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    return_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_sales_returns.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_item_master.id", ondelete="RESTRICT"), nullable=False)
    quantity_returned = mapped_column(Numeric(15, 4), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
