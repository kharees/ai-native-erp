from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalNumberSeries(Base):
    __tablename__ = 'universal_number_series'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = mapped_column(String(length=64), nullable=False) # e.g. Quotation, SalesOrder
    branch_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenant_branches.id", ondelete="CASCADE"), nullable=True)
    financial_year = mapped_column(String(length=16), nullable=True) # e.g. 26-27
    prefix = mapped_column(String(length=16), nullable=False) # e.g. INV, SO, QT
    current_sequence = mapped_column(Integer(), nullable=False, server_default=text('0'))
    padding = mapped_column(Integer(), nullable=False, server_default=text('4')) # e.g. 4 -> 0001
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
