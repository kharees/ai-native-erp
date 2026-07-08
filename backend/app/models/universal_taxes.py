from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalTaxConfiguration(Base):
    __tablename__ = 'universal_tax_configurations'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(length=128), nullable=False) # e.g. "Standard GST 18%"
    cgst_rate = mapped_column(Numeric(5, 2), nullable=False, server_default=text('0.00'))
    sgst_rate = mapped_column(Numeric(5, 2), nullable=False, server_default=text('0.00'))
    igst_rate = mapped_column(Numeric(5, 2), nullable=False, server_default=text('0.00'))
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalHSNSAC(Base):
    __tablename__ = 'universal_hsn_sac_codes'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    code = mapped_column(String(length=32), nullable=False) # HSN or SAC code
    description = mapped_column(Text(), nullable=True)
    code_type = mapped_column(String(length=16), nullable=False, server_default=text("'HSN'")) # HSN or SAC
    tax_config_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_tax_configurations.id", ondelete="SET NULL"), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
