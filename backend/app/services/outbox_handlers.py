"""
app/services/outbox_handlers.py
==================================
Placeholder event_type -> handler registry for outbox events
(app/models/outbox.py). NOT a poller/dispatcher -- there isn't one yet.
See docs/production-hardening.md's "Transactional outbox — write side
only, no relay/dispatcher" entry: nothing currently reads `outbox_events`
rows and actually publishes them (webhook, Celery task, message broker),
and building that relay is separate, larger infrastructure (its own
polling/locking strategy so two relay instances don't double-publish the
same row, retry/backoff for downstream delivery failures, an at-least-
once vs exactly-once decision) -- not built here.

This module exists so that relay, whenever it's built, has somewhere
real to route `event_type -> handler` rather than starting from nothing,
and so each event type's eventual real behavior (Sentry breadcrumb,
dashboard push, notification service, webhook, ...) has one obvious place
to live instead of being scattered across whatever calls enqueue_event().
Every handler below is a no-op/logging stub for exactly this reason --
replace the body, not the registration, once a real consumer exists.
"""

from typing import Awaitable, Callable

import structlog

from app.models.outbox import OutboxEvent

log = structlog.get_logger(__name__)

OutboxEventHandler = Callable[[OutboxEvent], Awaitable[None]]


async def handle_invoice_created(event: OutboxEvent) -> None:
    """No-op placeholder for "invoice.created" (see app/services/
    sales_fulfillment.py's create_invoice_with_stock_deduction, the only
    current producer -- convert_quotation_to_invoice delegates to it, so
    it produces this event too, not a separate one). Logs so the event's
    existence is visible/traceable even before a real consumer (Sentry,
    a dashboard update, a notification service, ...) exists."""
    log.info(
        "outbox_event_invoice_created",
        event_id=str(event.id),
        tenant_id=str(event.tenant_id),
        invoice_id=event.payload.get("invoice_id"),
        invoice_number=event.payload.get("invoice_number"),
        total_amount=event.payload.get("total_amount"),
    )


async def handle_journal_voucher_posted(event: OutboxEvent) -> None:
    """No-op placeholder for "journal_voucher.posted" (see
    app/crud/crud_finance_core.py's approve_journal_voucher, the original
    -- and until now, only -- outbox producer)."""
    log.info(
        "outbox_event_journal_voucher_posted",
        event_id=str(event.id),
        tenant_id=str(event.tenant_id),
        voucher_id=event.payload.get("voucher_id"),
        voucher_number=event.payload.get("voucher_number"),
    )


# Every event_type any producer currently writes must have an entry here,
# even if (like both above) it's just a logging no-op -- a future relay
# looking up event.event_type in this dict and finding nothing is a real
# gap, not an intentional one.
OUTBOX_EVENT_HANDLERS: dict[str, OutboxEventHandler] = {
    "invoice.created": handle_invoice_created,
    "journal_voucher.posted": handle_journal_voucher_posted,
}
