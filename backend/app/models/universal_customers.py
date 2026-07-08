from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class UniversalCustomerGroup(Base):
    __tablename__ = 'universal_customer_groups'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(length=128), nullable=False)
    description = mapped_column(Text(), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalCustomerType(Base):
    __tablename__ = 'universal_customer_types'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(length=128), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalCustomerCategory(Base):
    __tablename__ = 'universal_customer_categories'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(length=128), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalCustomer(Base):
    __tablename__ = 'universal_customers'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customer_groups.id", ondelete="SET NULL"), nullable=True)
    type_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customer_types.id", ondelete="SET NULL"), nullable=True)
    category_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customer_categories.id", ondelete="SET NULL"), nullable=True)
    name = mapped_column(String(length=255), nullable=False)
    email = mapped_column(String(length=320), nullable=True)
    phone = mapped_column(String(length=32), nullable=True)
    gst_number = mapped_column(String(length=15), nullable=True)
    pan = mapped_column(String(length=10), nullable=True)
    credit_limit = mapped_column(Numeric(15, 2), nullable=False, server_default=text('0.00'))
    credit_days = mapped_column(Integer(), nullable=False, server_default=text('0'))
    currency = mapped_column(String(length=3), nullable=False, server_default=text("'INR'"))
    status = mapped_column(String(length=32), nullable=False, server_default=text("'ACTIVE'"))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalCustomerContact(Base):
    __tablename__ = 'universal_customer_contacts'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(length=255), nullable=False)
    role = mapped_column(String(length=128), nullable=True)
    email = mapped_column(String(length=320), nullable=True)
    phone = mapped_column(String(length=32), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))

class UniversalCustomerAddress(Base):
    __tablename__ = 'universal_customer_addresses'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = mapped_column(UUID(as_uuid=True), ForeignKey("universal_customers.id", ondelete="CASCADE"), nullable=False, index=True)
    address_type = mapped_column(String(length=32), nullable=False) # BILLING, SHIPPING
    line1 = mapped_column(Text(), nullable=False)
    city = mapped_column(String(length=128), nullable=True)
    state = mapped_column(String(length=128), nullable=True)
    postal_code = mapped_column(String(length=32), nullable=True)
    country = mapped_column(String(length=128), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
