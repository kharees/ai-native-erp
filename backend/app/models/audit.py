from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- TenantAuditLog ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantAuditLog(Base):
    __tablename__ = 'tenant_audit_logs'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    user_id = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, index=True, )
    action_category = mapped_column(String(length=64), nullable=False, index=True, )
    action_type = mapped_column(String(length=64), nullable=False, index=True, )
    action_source = mapped_column(String(length=32), nullable=False, server_default=text("'API'"), )
    resource_id = mapped_column(String(length=128), nullable=True, index=True, )
    old_values = mapped_column(JSONB(astext_type=Text()), nullable=True, )
    new_values = mapped_column(JSONB(astext_type=Text()), nullable=True, )
    ip_address = mapped_column(String(length=64), nullable=True, )
    user_agent = mapped_column(String(length=512), nullable=True, )
    correlation_id = mapped_column(String(length=128), nullable=True, index=True, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), index=True, )
