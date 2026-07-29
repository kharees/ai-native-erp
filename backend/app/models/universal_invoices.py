from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalProformaInvoice(Base):
    __tablename__ = 'universal_proforma_invoices'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    sales_order_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_sales_orders.id", ondelete="SET NULL"), nullable=True)
    pi_number = mapped_column(String(length=64), nullable=False, unique=True)
    revision_number = mapped_column(Integer(), nullable=False, server_default=text('0'))
    status = mapped_column(String(length=32), nullable=False, server_default=text("'DRAFT'"))
    currency = mapped_column(String(length=3), nullable=False, server_default=text("'INR'"))
    is_tax_inclusive = mapped_column(Boolean(), nullable=False, server_default=text('FALSE'))
    subtotal = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    total_tax = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    total_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    # lazy="raise" prevents silent async lazy-loads (MissingGreenlet / N+1);
    # all read paths that serialize items must pass selectinload(items).
    items = relationship(
        "UniversalProformaInvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="raise",
    )

class UniversalProformaInvoiceItem(Base):
    __tablename__ = 'universal_proforma_invoice_items'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    pi_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_proforma_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_item_master.id", ondelete="RESTRICT"), nullable=False)
    quantity = mapped_column(Numeric(15, 4), nullable=False)
    unit_price = mapped_column(Numeric(15, 2), nullable=False)
    cgst_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    sgst_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    igst_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    line_total = mapped_column(Numeric(15, 2), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    invoice = relationship("UniversalProformaInvoice", back_populates="items")

class UniversalTaxInvoice(Base):
    __tablename__ = 'universal_tax_invoices'
    __table_args__ = (
        # Per-tenant uniqueness is the correct GST requirement: each registered
        # seller (tenant) must not reuse an invoice number within a financial
        # year.  A global unique index would wrongly prevent two different
        # tenants from independently issuing "INV/26-27/00001".
        # This composite constraint is the final DB-level backstop behind the
        # SELECT ... FOR UPDATE row-lock in
        # app/crud/universal_numbering.py::generate_next_number.
        UniqueConstraint("tenant_id", "invoice_number", name="uq_tax_invoices_tenant_invoice_number"),
    )
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    sales_order_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_sales_orders.id", ondelete="SET NULL"), nullable=True)
    invoice_number = mapped_column(String(length=64), nullable=False)
    status = mapped_column(String(length=32), nullable=False, server_default=text("'DRAFT'")) # DRAFT, ISSUED, CANCELLED
    currency = mapped_column(String(length=3), nullable=False, server_default=text("'INR'"))
    is_tax_inclusive = mapped_column(Boolean(), nullable=False, server_default=text('FALSE'))
    subtotal = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    total_cgst = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    total_sgst = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    total_igst = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    tds_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    total_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    # lazy="raise" prevents silent async lazy-loads (MissingGreenlet / N+1);
    # all read paths that serialize items must pass selectinload(items).
    items = relationship(
        "UniversalTaxInvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="raise",
    )

class UniversalTaxInvoiceItem(Base):
    __tablename__ = 'universal_tax_invoice_items'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_tax_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_item_master.id", ondelete="RESTRICT"), nullable=False)
    hsn_sac_code = mapped_column(String(length=32), nullable=True)
    quantity = mapped_column(Numeric(15, 4), nullable=False)
    unit_price = mapped_column(Numeric(15, 2), nullable=False)
    cgst_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    sgst_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    igst_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    line_total = mapped_column(Numeric(15, 2), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    invoice = relationship("UniversalTaxInvoice", back_populates="items")
