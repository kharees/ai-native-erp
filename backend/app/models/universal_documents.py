from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalDeliveryChallan(Base):
    __tablename__ = 'universal_delivery_challans'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    sales_order_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_sales_orders.id", ondelete="SET NULL"), nullable=True)
    tax_invoice_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_tax_invoices.id", ondelete="SET NULL"), nullable=True)
    challan_number = mapped_column(String(length=64), nullable=False, unique=True)
    status = mapped_column(String(length=32), nullable=False, server_default=text("'DRAFT'")) # DRAFT, SHIPPED, DELIVERED
    dispatch_date = mapped_column(DateTime(timezone=True), nullable=True)
    vehicle_number = mapped_column(String(length=64), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalDeliveryChallanItem(Base):
    __tablename__ = 'universal_delivery_challan_items'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    challan_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_delivery_challans.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_item_master.id", ondelete="RESTRICT"), nullable=False)
    quantity_dispatched = mapped_column(Numeric(15, 4), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalPackingSlip(Base):
    __tablename__ = 'universal_packing_slips'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    challan_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_delivery_challans.id", ondelete="SET NULL"), nullable=True)
    slip_number = mapped_column(String(length=64), nullable=False, unique=True)
    package_count = mapped_column(Integer(), nullable=False, server_default=text('1'))
    total_weight = mapped_column(Numeric(10, 2), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalPackingSlipItem(Base):
    __tablename__ = 'universal_packing_slip_items'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    slip_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_packing_slips.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_item_master.id", ondelete="RESTRICT"), nullable=False)
    quantity_packed = mapped_column(Numeric(15, 4), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
