from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalShippingCourier(Base):
    __tablename__ = 'universal_shipping_couriers'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    courier_name = mapped_column(String(length=128), nullable=False)
    tracking_url_template = mapped_column(String(length=256), nullable=True)
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalOrderDispatch(Base):
    __tablename__ = 'universal_order_dispatches'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    sales_order_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    courier_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_shipping_couriers.id", ondelete="RESTRICT"), nullable=True, index=True)
    tracking_number = mapped_column(String(length=128), nullable=True)
    shipping_charges = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    dispatch_status = mapped_column(String(length=32), nullable=False, server_default=text("'PENDING'")) # PENDING, SHIPPED, IN_TRANSIT, DELIVERED, RETURNED
    dispatched_at = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
