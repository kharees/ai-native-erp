from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- TenantDepartment ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantDepartment(Base):
    __tablename__ = 'tenant_departments'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    name = mapped_column(String(length=255), nullable=False, )
    code = mapped_column(String(length=64), nullable=False, )
    parent_id = mapped_column(UUID(), ForeignKey("tenant_departments.id", ondelete="SET NULL"), nullable=True, )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )

# --- TenantBranch ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantBranch(Base):
    __tablename__ = 'tenant_branches'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    name = mapped_column(String(length=255), nullable=False, )
    code = mapped_column(String(length=64), nullable=False, )
    address = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"), )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )

# --- TenantWarehouse ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantWarehouse(Base):
    __tablename__ = 'tenant_warehouses'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    branch_id = mapped_column(UUID(), ForeignKey("tenant_branches.id", ondelete="SET NULL"), nullable=True, )
    name = mapped_column(String(length=255), nullable=False, )
    code = mapped_column(String(length=64), nullable=False, )
    address = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"), )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
