from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalWarehouse(Base):
    __tablename__ = 'universal_warehouses'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    branch_id = mapped_column(UUID(as_uuid=True), ForeignKey('tenant_branches.id', ondelete='SET NULL'), nullable=True)
    code = mapped_column(String(64), nullable=False)
    name = mapped_column(String(255), nullable=False)
    type = mapped_column(String(64), nullable=True)
    status = mapped_column(String(32), server_default='active', nullable=False)
    capacity_sqft = mapped_column(Numeric(15, 2), server_default='0.0', nullable=False)
    metadata_ = mapped_column("metadata", JSONB(astext_type=Text()), server_default='{}', nullable=False)
    is_active = mapped_column(Boolean, server_default='true', nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), nullable=False)

class UniversalWarehouseZone(Base):
    __tablename__ = 'universal_warehouse_zones'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    warehouse_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_warehouses.id', ondelete='CASCADE'), nullable=False, index=True)
    code = mapped_column(String(64), nullable=False)
    name = mapped_column(String(255), nullable=False)
    type = mapped_column(String(64), nullable=True)
    is_active = mapped_column(Boolean, server_default='true', nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), nullable=False)

class UniversalWarehouseBin(Base):
    __tablename__ = 'universal_warehouse_bins'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    warehouse_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_warehouses.id', ondelete='CASCADE'), nullable=False, index=True)
    zone_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_warehouse_zones.id', ondelete='SET NULL'), nullable=True, index=True)
    code = mapped_column(String(64), nullable=False)
    name = mapped_column(String(255), nullable=False)
    aisle = mapped_column(String(64), nullable=True)
    rack = mapped_column(String(64), nullable=True)
    shelf = mapped_column(String(64), nullable=True)
    max_weight = mapped_column(Numeric(15, 2), server_default='0.0', nullable=False)
    max_volume = mapped_column(Numeric(15, 2), server_default='0.0', nullable=False)
    metadata_ = mapped_column("metadata", JSONB(astext_type=Text()), server_default='{}', nullable=False)
    is_active = mapped_column(Boolean, server_default='true', nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), nullable=False)

class UniversalStockBalance(Base):
    __tablename__ = 'universal_stock_balance'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_item_master.id', ondelete='CASCADE'), nullable=False, index=True)
    warehouse_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_warehouses.id', ondelete='CASCADE'), nullable=False, index=True)
    bin_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_warehouse_bins.id', ondelete='SET NULL'), nullable=True)
    quantity_on_hand = mapped_column(Numeric(15, 4), server_default='0.0000', nullable=False)
    quantity_reserved = mapped_column(Numeric(15, 4), server_default='0.0000', nullable=False)
    quantity_allocated = mapped_column(Numeric(15, 4), server_default='0.0000', nullable=False)
    last_transaction_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), nullable=False)

class UniversalStockTransaction(Base):
    __tablename__ = 'universal_stock_transactions'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_item_master.id', ondelete='CASCADE'), nullable=False, index=True)
    warehouse_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_warehouses.id', ondelete='CASCADE'), nullable=False, index=True)
    bin_id = mapped_column(UUID(as_uuid=True), ForeignKey('universal_warehouse_bins.id', ondelete='SET NULL'), nullable=True)
    transaction_type = mapped_column(String(32), nullable=False)
    reference_type = mapped_column(String(64), nullable=False)
    reference_id = mapped_column(String(128), nullable=True)
    quantity = mapped_column(Numeric(15, 4), nullable=False)
    metadata_ = mapped_column("metadata", JSONB(astext_type=Text()), server_default='{}', nullable=False)
    user_id = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), nullable=False)
