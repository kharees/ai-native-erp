from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- UserProfile ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    user_id = mapped_column(UUID(), nullable=False, unique=True, )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    first_name = mapped_column(String(length=128), nullable=True, )
    last_name = mapped_column(String(length=128), nullable=True, )
    profile_image = mapped_column(String(), nullable=True, )
    phone = mapped_column(String(), nullable=True, )
    timezone = mapped_column(String(), nullable=False, server_default=text("'UTC'"), )
    locale = mapped_column(String(), nullable=False, server_default=text("'en'"), )
    employee_code = mapped_column(String(length=64), nullable=True, index=True, )
    status = mapped_column(String(length=32), nullable=False, server_default=text("'Active'"), )
    designation = mapped_column(String(length=128), nullable=True, )
    department_id = mapped_column(UUID(), ForeignKey("tenant_departments.id", ondelete="SET NULL"), nullable=True, )
    branch_id = mapped_column(UUID(), ForeignKey("tenant_branches.id", ondelete="SET NULL"), nullable=True, )
    warehouse_id = mapped_column(UUID(), ForeignKey("tenant_warehouses.id", ondelete="SET NULL"), nullable=True, )
    manager_id = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    preferences = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"), )
    role = mapped_column(String(), nullable=False, server_default=text("'member'"), )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    last_login = mapped_column(DateTime(timezone=True), nullable=True, )
    created_by = mapped_column(UUID(), ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True, )
    updated_by = mapped_column(UUID(), ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True, )
    deleted_at = mapped_column(DateTime(timezone=True), nullable=True, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
