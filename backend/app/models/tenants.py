from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class Tenant(Base):
    __tablename__ = 'tenants'
    
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    name = mapped_column(String(255), nullable=False)
    slug = mapped_column(String(255), nullable=False, index=True, unique=True)
    plan = mapped_column(String(64), nullable=False, server_default='free')
    company_info = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default='{}')
    business_settings = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default='{}')
    is_active = mapped_column(Boolean, nullable=False, server_default='true')
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
