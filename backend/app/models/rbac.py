from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- TenantUserRole ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantUserRole(Base):
    __tablename__ = 'tenant_user_roles'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    user_id = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True, )
    role_id = mapped_column(UUID(), ForeignKey("tenant_roles.id", ondelete="CASCADE"), nullable=False, )
    branch_id = mapped_column(UUID(), ForeignKey("tenant_branches.id", ondelete="CASCADE"), nullable=True, )
    warehouse_id = mapped_column(UUID(), ForeignKey("tenant_warehouses.id", ondelete="CASCADE"), nullable=True, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    created_by = mapped_column(UUID(), ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True, )
# --- TenantRolePermission ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantRolePermission(Base):
    __tablename__ = 'tenant_role_permissions'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    role_id = mapped_column(UUID(), ForeignKey("tenant_roles.id", ondelete="CASCADE"), nullable=False, index=True, )
    permission_id = mapped_column(UUID(), ForeignKey("tenant_permissions.id", ondelete="CASCADE"), nullable=False, )
    conditions = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"), )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    created_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
# --- TenantPermission ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantPermission(Base):
    __tablename__ = 'tenant_permissions'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    module = mapped_column(String(length=64), nullable=False, index=True, )
    feature = mapped_column(String(length=64), nullable=False, index=True, )
    action = mapped_column(String(length=32), nullable=False, )
    description = mapped_column(Text(), nullable=True, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    deleted_at = mapped_column(DateTime(timezone=True), nullable=True, )
    created_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    updated_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
# --- TenantRole ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantRole(Base):
    __tablename__ = 'tenant_roles'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True, )
    name = mapped_column(String(length=128), nullable=False, )
    description = mapped_column(Text(), nullable=True, )
    is_system = mapped_column(Boolean(), nullable=False, server_default=text('FALSE'), )
    hierarchy_level = mapped_column(Integer(), nullable=False, server_default=text('100'), )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    deleted_at = mapped_column(DateTime(timezone=True), nullable=True, )
    created_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    updated_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
