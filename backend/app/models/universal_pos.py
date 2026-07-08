from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalPOSSession(Base):
    __tablename__ = 'universal_pos_sessions'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    session_status = mapped_column(String(length=32), nullable=False, server_default=text("'OPEN'")) # OPEN, CLOSED
    opening_balance = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    closing_balance = mapped_column(Numeric(15, 2), nullable=True)
    opened_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    closed_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalPOSHoldBill(Base):
    __tablename__ = 'universal_pos_hold_bills'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_pos_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    reference_name = mapped_column(String(length=128), nullable=True) # E.g. "Customer waiting in car"
    cart_data = mapped_column(JSONB(astext_type=Text()), nullable=False) # Stores the entire uncommitted cart items/discounts
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
