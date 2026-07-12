"""
tests/finance/test_outbox.py
===============================
Validates the transactional outbox foundation (Sprint 4 #37): posting a
journal voucher writes both the POSTED status and a matching outbox_events
row in the same commit.
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent

pytestmark = pytest.mark.asyncio


async def test_posting_voucher_enqueues_outbox_event(async_client: AsyncClient, db_session: AsyncSession, setup_tenant, auth_headers):
    grp_resp = await async_client.post(
        "/api/v1/finance-core/account-groups",
        json={"tenant_id": str(setup_tenant.id), "code": "OB-1000", "name": "Outbox Test", "category": "expense"},
        headers=auth_headers,
    )
    group_id = grp_resp.json()["id"]

    acc1 = (await async_client.post(
        "/api/v1/finance-core/accounts",
        json={"tenant_id": str(setup_tenant.id), "group_id": group_id, "account_code": "OB-5100", "name": "Outbox Expense"},
        headers=auth_headers,
    )).json()["id"]
    acc2 = (await async_client.post(
        "/api/v1/finance-core/accounts",
        json={"tenant_id": str(setup_tenant.id), "group_id": group_id, "account_code": "OB-1100", "name": "Outbox Cash"},
        headers=auth_headers,
    )).json()["id"]

    jv_resp = await async_client.post(
        "/api/v1/finance-core/journal-vouchers",
        json={
            "tenant_id": str(setup_tenant.id),
            "voucher_number": "OB-JV-001",
            "entry_date": datetime.now(timezone.utc).isoformat(),
            "lines": [
                {"account_id": acc1, "debit": 200.0, "credit": 0.0},
                {"account_id": acc2, "debit": 0.0, "credit": 200.0},
            ],
        },
        headers=auth_headers,
    )
    voucher_id = jv_resp.json()["id"]

    # No outbox event yet — only creating the voucher, not posting it.
    pre_stmt = select(OutboxEvent).where(OutboxEvent.event_type == "journal_voucher.posted")
    assert len((await db_session.execute(pre_stmt)).scalars().all()) == 0

    approve_resp = await async_client.post(
        f"/api/v1/finance-core/journals/{voucher_id}/approve", headers=auth_headers
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "posted"

    post_stmt = select(OutboxEvent).where(
        OutboxEvent.event_type == "journal_voucher.posted",
        OutboxEvent.tenant_id == setup_tenant.id,
    )
    events = (await db_session.execute(post_stmt)).scalars().all()
    assert len(events) == 1
    assert events[0].payload["voucher_id"] == voucher_id
    assert events[0].payload["voucher_number"] == "OB-JV-001"
    assert events[0].status == "pending"
