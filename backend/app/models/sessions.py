from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- TenantDevice ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantDevice(Base):
    __tablename__ = 'tenant_devices'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    user_id = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True, )
    device_fingerprint = mapped_column(String(length=255), nullable=False, )
    browser = mapped_column(String(length=64), nullable=True, )
    os = mapped_column(String(length=64), nullable=True, )
    last_ip_address = mapped_column(String(length=64), nullable=True, )
    is_trusted = mapped_column(Boolean(), nullable=False, server_default=text('FALSE'), )
    last_seen_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )

# --- TenantSession ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantSession(Base):
    __tablename__ = 'tenant_sessions'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    user_id = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True, )
    device_fingerprint = mapped_column(String(length=255), nullable=True, )
    ip_address = mapped_column(String(length=64), nullable=True, )
    browser = mapped_column(String(length=64), nullable=True, )
    os = mapped_column(String(length=64), nullable=True, )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    last_active_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    expires_at = mapped_column(DateTime(timezone=True), nullable=False, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
