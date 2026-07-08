from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- UniversalInventoryLedger ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalInventoryLedger(Base):
    __tablename__ = 'universal_inventory_ledger'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    item_id = mapped_column(UUID(), ForeignKey("universal_item_master.id", ondelete="CASCADE"), nullable=False, index=True, )
    warehouse_id = mapped_column(UUID(), ForeignKey("universal_warehouses.id", ondelete="CASCADE"), nullable=False, index=True, )
    bin_id = mapped_column(UUID(), ForeignKey("universal_warehouse_bins.id", ondelete="SET NULL"), nullable=True, index=True, )
    transaction_id = mapped_column(UUID(), ForeignKey("universal_stock_transactions.id", ondelete="SET NULL"), nullable=True, index=True, )
    quantity_before = mapped_column(Numeric(precision=15, scale=4), nullable=False, )
    movement_quantity = mapped_column(Numeric(precision=15, scale=4), nullable=False, )
    quantity_after = mapped_column(Numeric(precision=15, scale=4), nullable=False, )
    unit_cost = mapped_column(Numeric(precision=15, scale=2), nullable=False, server_default=text('0.0'), )
    total_cost = mapped_column(Numeric(precision=15, scale=2), nullable=False, server_default=text('0.0'), )
    reference_type = mapped_column(String(length=64), nullable=False, )
    reference_id = mapped_column(String(length=128), nullable=True, )
    user_id = mapped_column(UUID(), nullable=True, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
