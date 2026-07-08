from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base


# --- TenantFinanceLedger ---
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base

class TenantFinanceLedger(Base):
    __tablename__ = 'tenant_finance_ledgers'
    id = mapped_column(UUID(), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'), )
    tenant_id = mapped_column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True, )
    transaction_type = mapped_column(Enum('INCOME', 'EXPENSE', name='finance_transaction_type', schema='public'), nullable=False, )
    category = mapped_column(String(length=128), nullable=False, )
    amount = mapped_column(Numeric(precision=12, scale=2), nullable=False, )
    currency = mapped_column(String(length=3), nullable=False, server_default=text("'INR'"), )
    entry_date = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    description = mapped_column(Text(), nullable=True, )
    metadata_insights = mapped_column(JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"), )
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'), )
    created_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    updated_by = mapped_column(UUID(), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True, )
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'), )

from enum import Enum
class TransactionType(str, Enum):
    INCOME = 'income'
    EXPENSE = 'expense'
    TRANSFER = 'transfer'
