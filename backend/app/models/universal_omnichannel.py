from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalChannelConfiguration(Base):
    __tablename__ = 'universal_channel_configurations'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_name = mapped_column(String(length=64), nullable=False) # e.g. Amazon, Shopify, WhatsApp
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'))
    credentials = mapped_column(JSONB(astext_type=Text()), nullable=True) # API Keys, Secrets
    webhook_url = mapped_column(String(length=256), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalOrderChannelMapping(Base):
    __tablename__ = 'universal_order_channel_mappings'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_channel_configurations.id", ondelete="CASCADE"), nullable=False, index=True)
    sales_order_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_sales_orders.id", ondelete="CASCADE"), nullable=True, index=True)
    external_order_id = mapped_column(String(length=128), nullable=False, index=True)
    sync_status = mapped_column(String(length=32), nullable=False, server_default=text("'PENDING'")) # SYNCED, FAILED
    raw_payload = mapped_column(JSONB(astext_type=Text()), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalOmnichannelSyncLog(Base):
    __tablename__ = 'universal_omnichannel_sync_logs'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_channel_configurations.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = mapped_column(String(length=64), nullable=False) # ORDER_CREATED, PAYMENT_FAILED
    status = mapped_column(String(length=32), nullable=False) # SUCCESS, ERROR
    error_message = mapped_column(Text(), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
