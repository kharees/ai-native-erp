from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- UniversalBrand ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalBrand(Base):
    __tablename__ = 'universal_brands'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    name = mapped_column(String(length=255), nullable=False, )
    description = mapped_column(Text(), nullable=True, )
    website = mapped_column(String(length=255), nullable=True, )
    logo_url = mapped_column(String(length=1024), nullable=True, )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )

# --- UniversalCategory ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalCategory(Base):
    __tablename__ = 'universal_categories'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    name = mapped_column(String(length=255), nullable=False, )
    description = mapped_column(Text(), nullable=True, )
    parent_id = mapped_column(UUID(), ForeignKey("universal_categories.id", ondelete="SET NULL"), nullable=True, )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )

# --- UniversalItemMaster ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalItemMaster(Base):
    __tablename__ = 'universal_item_master'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    item_code = mapped_column(String(length=64), nullable=False, )
    sku = mapped_column(String(length=64), nullable=False, )
    barcode = mapped_column(String(length=128), nullable=True, )
    qr_code = mapped_column(String(length=128), nullable=True, )
    name = mapped_column(String(length=255), nullable=False, )
    short_name = mapped_column(String(length=128), nullable=True, )
    description = mapped_column(Text(), nullable=True, )
    status = mapped_column(String(length=32), nullable=False, server_default=text("'draft'"), )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    category_id = mapped_column(UUID(), ForeignKey("universal_categories.id", ondelete="SET NULL"), nullable=True, )
    brand_id = mapped_column(UUID(), ForeignKey("universal_brands.id", ondelete="SET NULL"), nullable=True, )
    uom_id = mapped_column(UUID(), ForeignKey("universal_uoms.id", ondelete="SET NULL"), nullable=True, )
    images = mapped_column(ARRAY(Text()), nullable=False, server_default=text("'{}'::text[]"), )
    documents = mapped_column(ARRAY(Text()), nullable=False, server_default=text("'{}'::text[]"), )
    notes = mapped_column(Text(), nullable=True, )
    variants = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"), )
    attributes = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"), )
    created_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    updated_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )

# --- UniversalUOM ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalUOM(Base):
    __tablename__ = 'universal_uoms'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    name = mapped_column(String(length=128), nullable=False, )
    abbreviation = mapped_column(String(length=32), nullable=False, )
    base_uom_id = mapped_column(UUID(), ForeignKey("universal_uoms.id", ondelete="SET NULL"), nullable=True, )
    conversion_factor = mapped_column(Numeric(precision=18, scale=6), nullable=False, server_default=text('1.0'), )
    decimal_precision = mapped_column(Integer(), nullable=False, server_default=text('0'), )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
