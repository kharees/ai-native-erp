from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalCustomerPriceList(Base):
    __tablename__ = 'universal_customer_price_lists'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_group_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customer_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_item_master.id", ondelete="CASCADE"), nullable=False, index=True)
    price = mapped_column(Numeric(15, 2), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalSalesQuotation(Base):
    __tablename__ = 'universal_sales_quotations'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    quotation_number = mapped_column(String(length=64), nullable=False, unique=True)
    revision_number = mapped_column(Integer(), nullable=False, server_default=text('0'))
    status = mapped_column(String(length=32), nullable=False, server_default=text("'DRAFT'"))
    total_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    valid_until = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    # lazy="raise" ensures selectinload is used on every read path that
    # serializes items — prevents silent N+1 / MissingGreenlet errors.
    items = relationship(
        "UniversalSalesQuotationItem",
        back_populates="quotation",
        cascade="all, delete-orphan",
        lazy="raise",
    )

class UniversalSalesQuotationItem(Base):
    __tablename__ = 'universal_sales_quotation_items'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    quotation_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_sales_quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_item_master.id", ondelete="RESTRICT"), nullable=False)
    quantity = mapped_column(Numeric(15, 4), nullable=False)
    unit_price = mapped_column(Numeric(15, 2), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    quotation = relationship("UniversalSalesQuotation", back_populates="items")

class UniversalSalesOrder(Base):
    __tablename__ = 'universal_sales_orders'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    quotation_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_sales_quotations.id", ondelete="SET NULL"), nullable=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_number = mapped_column(String(length=64), nullable=False, unique=True)
    status = mapped_column(String(length=32), nullable=False, server_default=text("'PENDING'"))
    approval_status = mapped_column(String(length=32), nullable=False, server_default=text("'PENDING'"))
    total_amount = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    # lazy="raise" ensures selectinload is used on every read path that
    # serializes items — prevents silent N+1 / MissingGreenlet errors.
    items = relationship(
        "UniversalSalesOrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="raise",
    )

class UniversalSalesOrderItem(Base):
    __tablename__ = 'universal_sales_order_items'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_item_master.id", ondelete="RESTRICT"), nullable=False)
    quantity = mapped_column(Numeric(15, 4), nullable=False)
    unit_price = mapped_column(Numeric(15, 2), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    order = relationship("UniversalSalesOrder", back_populates="items")
