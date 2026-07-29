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

    try:
        obj = await crud.create_payment_receipt(db, tenant_id, payload)
        if claim.should_complete:
            await complete_idempotency_key(db, tenant_id, "payments.receipts", idempotency_key, obj.id, response_body)
        return obj
    except Exception:
        # See release_idempotency_key's own docstring: without this, a
        # request that fails AFTER a successful claim (a business-rule
        # rejection, a downstream error, anything) leaves the claim row
        # "pending" forever, and every legitimate retry with the same key
        # gets a permanent 409 instead of a real second attempt.
        if claim.should_complete:
            await db.rollback()
            await release_idempotency_key(db, tenant_id, "payments.receipts", idempotency_key)
        raise

Stale-claim recovery
----------------------
A claim that's still "pending" after `_STALE_CLAIM_TTL` (24 hours) is
treated as abandoned -- e.g. a process crash between claim_idempotency_key's
commit and the caller reaching complete_idempotency_key/release_idempotency_key,
or a claim stuck from before release_idempotency_key existed at all. Rather
than block that key's endpoint forever, claim_idempotency_key deletes the
stale row and re-claims it as if it were new. A claim genuinely still
in-flight (younger than the TTL) still returns conflict=True as before --
this is a dead-claim recovery mechanism, not a way to race a real
concurrent request.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyKey

# How long a "pending" claim is trusted to genuinely still be in-flight
# before it's assumed abandoned (crashed process, unhandled exception from
# before release_idempotency_key existed, etc.) and safe to delete and
# re-claim. Deliberately generous -- 24h is far longer than any real
# request should ever take, so this only ever rescues genuinely stuck
# claims, never races a request that's merely slow.
_STALE_CLAIM_TTL = timedelta(hours=24)


def _is_stale(created_at: datetime) -> bool:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - created_at) > _STALE_CLAIM_TTL


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
    db: AsyncSession, tenant_id: uuid.UUID, endpoint: str, key: str | None, _retry: bool = False,
) -> IdempotencyClaim:
    """
    No-op (returns should_complete=False, meaning "just proceed normally")
    when `key` is None — the Idempotency-Key header is optional, so requests
    that don't send it behave exactly as before this feature existed.

    _retry: internal only, never pass explicitly. Set when this function
    calls itself once after deleting a stale abandoned claim (see module
    docstring) — bounds stale-claim recovery to a single retry rather than
    recursing indefinitely if something keeps re-losing the race.
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
        if (
            not _retry
            and existing is not None
            and existing.status == "pending"
            and _is_stale(existing.created_at)
        ):
            # Abandoned claim (see module docstring) — reclaim it rather
            # than leaving this key permanently 409ing.
            await db.delete(existing)
            await db.commit()
            return await claim_idempotency_key(db, tenant_id, endpoint, key, _retry=True)
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


async def release_idempotency_key(
    db: AsyncSession, tenant_id: uuid.UUID, endpoint: str, key: str | None
) -> None:
    """
    Deletes a still-"pending" claim row so a legitimate retry with the same
    key doesn't get permanently 409'd by claim_idempotency_key -- the fix
    for the documented gap where a request that fails AFTER a successful
    claim (a business-rule rejection like insufficient stock, or any other
    exception) used to leave the claim stuck forever.

    Call this OUTSIDE the failed transaction the claimed operation ran in
    -- i.e. only after that transaction has already been rolled back (via
    `async with db.begin():` exiting on exception, or an explicit
    `await db.rollback()` first if the caller isn't using a nested
    `db.begin()` block). Deleting the row while still inside a transaction
    that's about to roll back would just get rolled back too, right back
    to the stuck state this exists to fix. Commits its own work, same as
    claim_idempotency_key's initial insert -- so the release survives even
    though the operation it was guarding did not.

    No-op when:
      - `key` is None (mirrors claim_idempotency_key's own no-op — nothing
        was ever claimed).
      - No row exists for this (tenant_id, endpoint, key) (already
        released, or this call is racing a concurrent release/completion).
      - The row is not "pending" (e.g. "completed" — a completed claim
        must never be deleted, that would defeat replay for a legitimately
        finished request; only the request that actually finished it calls
        complete_idempotency_key, never this function).
    """
    if not key:
        return
    stmt = select(IdempotencyKey).where(
        IdempotencyKey.tenant_id == tenant_id,
        IdempotencyKey.endpoint == endpoint,
        IdempotencyKey.key == key,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None or row.status != "pending":
        return
    await db.delete(row)
    await db.commit()
