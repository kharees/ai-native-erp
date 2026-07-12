"""
app/services/idempotency.py
============================
Helper for endpoints that accept an optional `Idempotency-Key` header on
create requests, so a client retrying after a timeout gets the original
response back instead of creating a second resource.

Usage in a route handler
-------------------------
    claim = await claim_idempotency_key(db, tenant_id, "payments.receipts", idempotency_key)
    if claim.replay_response is not None:
        return claim.replay_response
    if claim.conflict:
        raise HTTPException(409, "Request with this idempotency key is already being processed.")

    obj = await crud.create_payment_receipt(db, tenant_id, payload)

    if claim.should_complete:
        await complete_idempotency_key(db, tenant_id, "payments.receipts", idempotency_key, obj.id, response_body)

    return obj
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyKey


@dataclass
class IdempotencyClaim:
    # Set when a prior request with this key already completed — the
    # caller should return this instead of re-running the create.
    replay_response: Any | None = None
    # True when a prior request with this key is still in flight (or died
    # mid-request without completing) — the caller should reject with 409
    # rather than risk a second concurrent create.
    conflict: bool = False
    # True when this call won the claim and should call
    # complete_idempotency_key() once the resource is created.
    should_complete: bool = False


async def claim_idempotency_key(
    db: AsyncSession, tenant_id: uuid.UUID, endpoint: str, key: str | None
) -> IdempotencyClaim:
    """
    No-op (returns should_complete=False, meaning "just proceed normally")
    when `key` is None — the Idempotency-Key header is optional, so requests
    that don't send it behave exactly as before this feature existed.
    """
    if not key:
        return IdempotencyClaim(should_complete=False)

    claim_row = IdempotencyKey(tenant_id=tenant_id, endpoint=endpoint, key=key, status="pending")
    db.add(claim_row)
    try:
        await db.flush()
        # Must be a real commit, not flush: this claim row is how a second,
        # concurrent request with the same key gets rejected below (via the
        # IntegrityError on the unique constraint) instead of racing this one
        # through resource creation. flush() only makes the row visible on
        # this connection's own open transaction — a concurrent request runs
        # on a different session and cannot see it until this commits.
        await db.commit()
        return IdempotencyClaim(should_complete=True)
    except IntegrityError:
        # Unique (tenant_id, endpoint, key) violation — someone already
        # claimed this key. Roll back our failed insert, then look at what
        # they left behind.
        await db.rollback()
        existing = (
            await db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id,
                    IdempotencyKey.endpoint == endpoint,
                    IdempotencyKey.key == key,
                )
            )
        ).scalar_one_or_none()
        if existing is not None and existing.status == "completed":
            return IdempotencyClaim(replay_response=existing.response_body)
        return IdempotencyClaim(conflict=True)


async def complete_idempotency_key(
    db: AsyncSession, tenant_id: uuid.UUID, endpoint: str, key: str,
    resource_id: uuid.UUID, response_body: dict,
) -> None:
    stmt = select(IdempotencyKey).where(
        IdempotencyKey.tenant_id == tenant_id,
        IdempotencyKey.endpoint == endpoint,
        IdempotencyKey.key == key,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return
    row.status = "completed"
    row.resource_id = resource_id
    row.response_body = response_body
    # Deliberately flush, not commit: the caller (see module docstring)
    # calls this right after creating the resource, in the same request. A
    # flush keeps "resource created" and "idempotency key marked complete"
    # in one transaction, committed together at the end of the request by
    # get_db()'s unit-of-work. Previously these were two independent
    # commits — a crash between them could leave a created resource with no
    # completed idempotency record, so a client retry would create a
    # second, duplicate resource, defeating the whole point of this module.
    await db.flush()
