"""
tests/test_unit_of_work.py
===========================
Sprint 5 (#1): proves the actual atomicity contract the unit-of-work
refactor depends on.

Every other test file in this suite exercises the API through
`conftest.py`'s `async_client`, which overrides `get_db()` to hand every
request the *same* already-open, never-actually-committed `db_session`
fixture (rolled back at teardown for per-test isolation — see
conftest.py). That is correct for test isolation, but it means those
tests never invoke `app.core.database.db_session()` / `get_db()`'s real
commit-on-success / rollback-on-exception boundary against the database,
so they cannot prove whether a mid-operation failure actually rolls back
an earlier write in the same request.

These tests bypass the app and the shared test-session fixture entirely
and drive `app.core.database.db_session()` directly, on its own real
connection — the same context manager `get_db()` wraps every real request
in — to prove:
  1. A multi-step write followed by a failure rolls back *everything*,
     including steps that individually succeeded (flushed) before the
     failure. This is only true because app/crud no longer calls
     `db.commit()` internally (Sprint 5 #1) — before that refactor, each
     CRUD call committed its own step independently, so a failure in step
     2 would still leave step 1's write durably persisted.
  2. A multi-step write with no failure persists everything together,
     visible from a completely separate connection afterward.

Because this exercises real commits against the real database (unlike
every other test in this suite, which always rolls back), each test
creates its own throwaway tenant and tears it down explicitly in a
`finally` block rather than relying on the shared `db_session`/
`setup_tenant` fixtures, which live inside a transaction that is never
actually committed and so would not be visible on this separate connection.
"""
import uuid

import pytest
from sqlalchemy import delete, select

from app.core.database import db_session
from app.crud import universal_inventory as inv_crud
from app.models.tenants import Tenant
from app.models.universal_inventory import UniversalCategory
from app.schemas.universal_inventory import UniversalCategoryCreate

pytestmark = pytest.mark.asyncio


async def _make_real_tenant() -> uuid.UUID:
    async with db_session() as db:
        tenant = Tenant(name="UOW Test Tenant", slug=f"uow-test-{uuid.uuid4().hex[:12]}", plan="enterprise")
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)
        return tenant.id


async def _delete_tenant(tenant_id: uuid.UUID) -> None:
    async with db_session() as db:
        await db.execute(delete(UniversalCategory).where(UniversalCategory.tenant_id == tenant_id))
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def test_failure_after_partial_write_rolls_back_everything():
    tenant_id = await _make_real_tenant()
    marker = f"UOW-FAIL-{uuid.uuid4().hex[:8]}"

    try:
        with pytest.raises(RuntimeError):
            async with db_session() as db:
                # Step 1 of a hypothetical multi-step business operation:
                # succeeds and is flushed (visible on this connection), but
                # not yet committed.
                await inv_crud.create_category(
                    db, tenant_id, UniversalCategoryCreate(name=marker, description="uow test")
                )
                # Step 2 fails. Nothing in app/crud calls db.commit()
                # anymore, so step 1's flush has no independent durability
                # — it lives or dies with this transaction.
                raise RuntimeError("simulated failure in a later step")

        # Verify from a brand-new session/connection that step 1 never
        # persisted.
        async with db_session() as verify_db:
            result = await verify_db.execute(
                select(UniversalCategory).where(
                    UniversalCategory.tenant_id == tenant_id,
                    UniversalCategory.name == marker,
                )
            )
            assert result.scalar_one_or_none() is None
    finally:
        await _delete_tenant(tenant_id)


async def test_multi_step_success_persists_together():
    tenant_id = await _make_real_tenant()
    marker = f"UOW-OK-{uuid.uuid4().hex[:8]}"

    try:
        async with db_session() as db:
            cat1 = await inv_crud.create_category(
                db, tenant_id, UniversalCategoryCreate(name=f"{marker}-1", description="uow test")
            )
            cat2 = await inv_crud.create_category(
                db, tenant_id, UniversalCategoryCreate(name=f"{marker}-2", description="uow test")
            )
            assert cat1.id is not None
            assert cat2.id is not None
            # No commit() call anywhere above — db_session() commits once,
            # on clean exit of this block.

        async with db_session() as verify_db:
            result = await verify_db.execute(
                select(UniversalCategory).where(
                    UniversalCategory.tenant_id == tenant_id,
                    UniversalCategory.name.in_([f"{marker}-1", f"{marker}-2"]),
                )
            )
            names = {row.name for row in result.scalars().all()}
            assert names == {f"{marker}-1", f"{marker}-2"}
    finally:
        await _delete_tenant(tenant_id)
