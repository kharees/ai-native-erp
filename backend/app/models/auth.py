from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class UserAccount(Base):
    __tablename__ = 'user_accounts'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=text('uuid_generate_v4()'))
    email = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password = mapped_column(String(255), nullable=False)
    is_active = mapped_column(Boolean(), nullable=False, server_default=text('TRUE'))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=text('now()'))
