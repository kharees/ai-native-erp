from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- UniversalBatchStock ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalBatchStock(Base):
    __tablename__ = 'universal_batch_stock'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    batch_id = mapped_column(UUID(), ForeignKey("universal_batch_master.id", ondelete="CASCADE"), nullable=False, index=True, )
    warehouse_id = mapped_column(UUID(), ForeignKey("universal_warehouses.id", ondelete="CASCADE"), nullable=False, index=True, )
    bin_id = mapped_column(UUID(), ForeignKey("universal_warehouse_bins.id", ondelete="SET NULL"), nullable=True, index=True, )
    quantity_on_hand = mapped_column(Numeric(precision=15, scale=4), nullable=False, server_default=text('0.0000'), )
    last_transaction_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )

# --- UniversalSerialMaster ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalSerialMaster(Base):
    __tablename__ = 'universal_serial_master'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    item_id = mapped_column(UUID(), ForeignKey("universal_item_master.id", ondelete="CASCADE"), nullable=False, index=True, )
    batch_id = mapped_column(UUID(), ForeignKey("universal_batch_master.id", ondelete="SET NULL"), nullable=True, index=True, )
    serial_number = mapped_column(String(length=128), nullable=False, )
    status = mapped_column(String(length=32), nullable=False, server_default=text("'available'"), )
    warehouse_id = mapped_column(UUID(), ForeignKey("universal_warehouses.id", ondelete="SET NULL"), nullable=True, index=True, )
    bin_id = mapped_column(UUID(), ForeignKey("universal_warehouse_bins.id", ondelete="SET NULL"), nullable=True, index=True, )
    warranty_expiry = mapped_column(Date(), nullable=True, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )

# --- UniversalBatchMaster ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalBatchMaster(Base):
    __tablename__ = 'universal_batch_master'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    item_id = mapped_column(UUID(), ForeignKey("universal_item_master.id", ondelete="CASCADE"), nullable=False, index=True, )
    batch_number = mapped_column(String(length=128), nullable=False, )
    mfg_date = mapped_column(Date(), nullable=True, )
    expiry_date = mapped_column(Date(), nullable=True, index=True, )
    shelf_life_days = mapped_column(Integer(), nullable=True, )
    status = mapped_column(String(length=32), nullable=False, server_default=text("'active'"), )
    cost_multiplier = mapped_column(Numeric(precision=5, scale=4), nullable=False, server_default=text('1.0000'), )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
