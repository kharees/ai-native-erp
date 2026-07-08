from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- InventoryItem ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class InventoryItem(Base):
    __tablename__ = 'inventory_items'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    sku = mapped_column(String(length=64), nullable=False, )
    name = mapped_column(String(length=255), nullable=False, )
    description = mapped_column(Text(), nullable=True, )
    category = mapped_column(String(length=128), nullable=True, )
    sub_category = mapped_column(String(length=128), nullable=True, )
    brand = mapped_column(String(length=128), nullable=True, )
    tags = mapped_column(ARRAY(Text()), nullable=False, server_default=text("'{}'::text[]"), )
    unit_price = mapped_column(Numeric(precision=18, scale=4), nullable=False, server_default=text('0'), )
    cost_price = mapped_column(Numeric(precision=18, scale=4), nullable=False, server_default=text('0'), )
    currency = mapped_column(String(length=3), nullable=False, server_default=text("'USD'"), )
    quantity_on_hand = mapped_column(Integer(), nullable=False, server_default=text('0'), )
    reorder_level = mapped_column(Integer(), nullable=False, server_default=text('0'), )
    unit_of_measure = mapped_column(String(length=32), nullable=False, server_default=text("'unit'"), )
    attributes = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"), )
    status = mapped_column(String(length=32), nullable=False, server_default=text("'draft'"), )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    created_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    updated_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
