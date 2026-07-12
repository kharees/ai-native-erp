"""
app/services/outbox.py
========================
Transactional outbox write side — see app/models/outbox.py for the full
rationale. Usage:

    from app.services.outbox import enqueue_event

    async def approve_journal_voucher(self, db, id, tenant_id, user_id):
        ...
        db_voucher.status = JournalStatus.POSTED
        db.add(db_voucher)
        await enqueue_event(db, tenant_id, "journal_voucher.posted", {
            "voucher_id": str(db_voucher.id),
            "voucher_number": db_voucher.voucher_number,
        })
        await db.flush()   # both rows go to the DB together
        ...                # caller's existing commit covers both

`enqueue_event` deliberately does not commit — the caller's existing unit
of work does, so the event and the business change it describes are
always written atomically together.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent


async def enqueue_event(
    db: AsyncSession, tenant_id: uuid.UUID, event_type: str, payload: dict[str, Any]
) -> OutboxEvent:
    event = OutboxEvent(tenant_id=tenant_id, event_type=event_type, payload=payload)
    db.add(event)
    return event
