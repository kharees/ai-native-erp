import uuid
from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class OutboxEvent(Base):
    """
    Transactional outbox (audit #37) — nothing in the backend emitted
    domain events (invoice created, stock adjusted, voucher posted) for
    webhooks or downstream/AI consumption; any future integration had to
    poll instead of subscribe, and adding pub/sub naively later (write to
    DB, then separately publish to a broker) risks the classic dual-write
    problem: one write can succeed while the other fails, with no way to
    tell from outside which happened.

    The fix is this table: `enqueue_event()` (app/services/outbox.py) does
    a plain `db.add()`, no commit — the event row is written in the SAME
    transaction as whatever business change it describes, using the same
    unit-of-work the caller already has open. Either both commit or
    neither does; there's no window where one exists without the other.

    This is the write side only. A relay/dispatcher that polls
    `status='pending'` rows and actually publishes them (to a webhook,
    Celery task, message broker, etc.) is a separate, larger piece of
    infrastructure not built here — see docs/production-hardening.md.
    """
    __tablename__ = 'outbox_events'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = mapped_column(String(128), nullable=False, index=True)
    payload = mapped_column(JSONB(astext_type=Text()), nullable=False)
    status = mapped_column(String(16), nullable=False, server_default=text("'pending'"))  # pending | processed | failed
    created_at = mapped_column(DateTime(timezone=True), server_default=text('now()'), nullable=False)
    processed_at = mapped_column(DateTime(timezone=True), nullable=True)
