import uuid
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class IdempotencyKey(Base):
    """
    Tracks client-supplied `Idempotency-Key` header values for POST
    endpoints where a retried request (e.g. a POS/mobile client retrying
    after a timeout) must not create a second resource.

    Claiming a key is a single atomic INSERT protected by the unique
    constraint below: if two concurrent requests race with the same key,
    only one INSERT succeeds — the loser sees a unique-violation and reads
    back whichever state the winner left (completed -> replay its response,
    still pending -> 409, ask the caller to retry).
    """
    __tablename__ = 'idempotency_keys'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    # Identifies which endpoint/resource type this key was scoped to, e.g.
    # "payments.receipts" — the same key string reused against a different
    # endpoint is a different claim, not a collision.
    endpoint = mapped_column(String(128), nullable=False)
    key = mapped_column(String(255), nullable=False)
    status = mapped_column(String(16), nullable=False, server_default=text("'pending'"))  # pending | completed
    resource_id = mapped_column(UUID(as_uuid=True), nullable=True)
    response_body = mapped_column(JSONB(astext_type=Text()), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), onupdate=text('now()'), nullable=False)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'endpoint', 'key', name='uq_idempotency_tenant_endpoint_key'),
    )
