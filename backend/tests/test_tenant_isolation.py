"""
tests/test_tenant_isolation.py
================================
Sprint 5 (#3): regression tests for the real cross-tenant leaks found and
fixed in this sprint. Each test creates a resource as `auth_headers`'
tenant, then attempts the same action as `alt_tenant_headers`' tenant
(conftest.py's second, independent tenant fixture) and asserts it's
rejected — not silently succeeding against the wrong tenant's data.

Before this sprint, every one of these calls succeeded against the other
tenant's resource:
  - migration execute/pause/resume/cancel/rollback/reconcile
    (app/services/migration_execution_engine.py had no tenant_id filter
    at all, and the endpoints computed tenant_id but never passed it in)
  - migration validate (app/services/migration_engine.py::validate_session)
  - migration cleansing analysis (app/api/v1/endpoints/migration_hub.py::
    analyze_cleansing_rules never checked session ownership)
  - migration AI copilot data-quality/cleansing-suggestions/chat
  - ERP connector sync (defense-in-depth; not reachable via the existing
    single caller, which already checked, but the service function itself
    had no filter)
  - payment allocation (app/crud/universal_payments.py::create_payment_allocation
    used db.get() by primary key only, no tenant filter, and could both
    read and mutate another tenant's receipt/wallet)
"""
import io
import uuid

import pandas as pd
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def _upload_session(async_client: AsyncClient, headers) -> str:
    df = pd.DataFrame({"Name": ["Test"]})
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    resp = await async_client.post(
        "/api/v1/migration/upload?entity_type=CUSTOMER",
        headers=headers,
        files={"file": ("test.csv", buf, "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.parametrize(
    "action,expected_status_field",
    [
        ("execute", "IMPORTING"),
        ("pause", "PAUSED"),
        ("resume", "IMPORTING"),
        ("cancel", "CANCELLING"),
    ],
)
async def test_migration_execution_actions_reject_foreign_tenant(
    async_client: AsyncClient, auth_headers, alt_tenant_headers, action, expected_status_field
):
    session_id = await _upload_session(async_client, auth_headers)

    foreign_resp = await async_client.post(
        f"/api/v1/migration/execution/{session_id}/{action}", headers=alt_tenant_headers
    )
    assert foreign_resp.status_code == 404

    owner_resp = await async_client.post(
        f"/api/v1/migration/execution/{session_id}/{action}", headers=auth_headers
    )
    assert owner_resp.status_code == 200
    assert owner_resp.json()["status"] == expected_status_field


async def test_migration_rollback_rejects_foreign_tenant(
    async_client: AsyncClient, auth_headers, alt_tenant_headers
):
    session_id = await _upload_session(async_client, auth_headers)

    foreign_resp = await async_client.post(
        f"/api/v1/migration/execution/{session_id}/rollback",
        headers=alt_tenant_headers,
        json={"partial": False, "record_ids": []},
    )
    assert foreign_resp.status_code == 404


async def test_migration_reconcile_rejects_foreign_tenant(
    async_client: AsyncClient, auth_headers, alt_tenant_headers
):
    session_id = await _upload_session(async_client, auth_headers)

    foreign_resp = await async_client.post(
        f"/api/v1/migration/execution/{session_id}/reconcile", headers=alt_tenant_headers
    )
    assert foreign_resp.status_code == 404


async def test_migration_validate_rejects_foreign_tenant(
    async_client: AsyncClient, auth_headers, alt_tenant_headers
):
    session_id = await _upload_session(async_client, auth_headers)

    foreign_resp = await async_client.post(
        f"/api/v1/migration/{session_id}/validate",
        headers=alt_tenant_headers,
        json={"mapping_config": {}, "transformation_rules": []},
    )
    assert foreign_resp.status_code == 404


async def test_migration_cleansing_rejects_foreign_tenant(
    async_client: AsyncClient, auth_headers, alt_tenant_headers
):
    session_id = await _upload_session(async_client, auth_headers)

    foreign_resp = await async_client.get(
        f"/api/v1/migration/{session_id}/cleansing", headers=alt_tenant_headers
    )
    assert foreign_resp.status_code == 403

    owner_resp = await async_client.get(
        f"/api/v1/migration/{session_id}/cleansing", headers=auth_headers
    )
    assert owner_resp.status_code == 200


async def test_migration_ai_copilot_endpoints_reject_foreign_tenant(
    async_client: AsyncClient, auth_headers, alt_tenant_headers
):
    session_id = await _upload_session(async_client, auth_headers)

    dq_resp = await async_client.get(
        f"/api/v1/migration/ai-copilot/{session_id}/data-quality", headers=alt_tenant_headers
    )
    assert dq_resp.status_code == 404

    # suggest_cleansing_rules and natural_language_query treat "not mine"
    # the same as "doesn't exist" (return an empty/graceful response
    # instead of raising) — the fix is that neither leaks the other
    # tenant's session content, not that they change status code shape.
    cs_resp = await async_client.get(
        f"/api/v1/migration/ai-copilot/{session_id}/cleansing-suggestions", headers=alt_tenant_headers
    )
    assert cs_resp.status_code == 200
    assert cs_resp.json()["suggestions"] == []

    chat_resp = await async_client.post(
        f"/api/v1/migration/ai-copilot/{session_id}/chat",
        headers=alt_tenant_headers,
        json={"query": "summary"},
    )
    assert chat_resp.status_code == 200
    assert "couldn't find" in chat_resp.json()["response"].lower()


async def test_erp_connector_sync_rejects_foreign_tenant(
    async_client: AsyncClient, auth_headers, alt_tenant_headers
):
    create_resp = await async_client.post(
        "/api/v1/migration/connectors",
        headers=auth_headers,
        json={"name": "Isolation Test ERP", "erp_type": "TALLY", "credentials": {"username": "a"}},
    )
    assert create_resp.status_code == 201, create_resp.text
    connector_id = create_resp.json()["id"]

    foreign_resp = await async_client.post(
        f"/api/v1/migration/connectors/{connector_id}/sync?entity_type=CUSTOMER",
        headers=alt_tenant_headers,
    )
    assert foreign_resp.status_code == 404


async def test_payment_allocation_does_not_mutate_foreign_tenant_receipt(
    async_client: AsyncClient, db_session: AsyncSession, auth_headers, alt_tenant_headers, setup_tenant
):
    customer_resp = await async_client.post(
        "/api/v1/omnichannel-billing/customers/",
        headers=auth_headers,
        json={"name": "Isolation Customer", "email": "isolation@example.com"},
    )
    assert customer_resp.status_code == 201, customer_resp.text
    customer_id = customer_resp.json()["id"]

    # Inserted directly rather than via POST /receipts: that endpoint has a
    # pre-existing, unrelated Decimal/float bug on a customer's first
    # receipt (app/crud/universal_payments.py::create_payment_receipt,
    # `wallet.balance += Decimal(...)` against a freshly-constructed
    # wallet's still-float balance) — out of scope for a tenant-isolation
    # fix, not touched here.
    from decimal import Decimal
    from app.models.universal_invoices import UniversalTaxInvoice
    from app.models.universal_payments import UniversalPaymentReceipt

    invoice = UniversalTaxInvoice(
        tenant_id=setup_tenant.id,
        customer_id=uuid.UUID(customer_id),
        invoice_number=f"ISO-INV-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(invoice)
    await db_session.flush()

    receipt = UniversalPaymentReceipt(
        tenant_id=setup_tenant.id,
        customer_id=uuid.UUID(customer_id),
        receipt_number=f"ISO-{uuid.uuid4().hex[:8]}",
        payment_mode="cash",
        amount_received=Decimal("500.00"),
        unallocated_amount=Decimal("500.00"),
    )
    db_session.add(receipt)
    await db_session.commit()
    await db_session.refresh(receipt)
    receipt_id = str(receipt.id)
    original_unallocated = float(receipt.unallocated_amount)

    # alt_tenant_headers' tenant tries to allocate against a receipt_id it
    # does not own. Before the fix, crud.create_payment_allocation used
    # db.get() (primary-key-only lookup, no tenant filter) and this call
    # would silently succeed, decrementing tenant A's receipt and wallet.
    alloc_resp = await async_client.post(
        "/api/v1/omnichannel-billing/payments/allocations",
        headers=alt_tenant_headers,
        json={"receipt_id": receipt_id, "invoice_id": str(invoice.id), "allocated_amount": 100.0},
    )
    # The allocation record itself is still created (pre-existing business
    # logic: an allocation with no matching receipt is a silent no-op, not
    # an error — unchanged by this fix) but it must not touch tenant A's data.
    assert alloc_resp.status_code == 201, alloc_resp.text

    from sqlalchemy import select
    from app.models.universal_payments import UniversalPaymentReceipt

    check = await db_session.execute(
        select(UniversalPaymentReceipt).where(UniversalPaymentReceipt.id == receipt_id)
    )
    receipt_after = check.scalar_one()
    assert float(receipt_after.unallocated_amount) == float(original_unallocated)


# ---------------------------------------------------------------------------
# Sprint 5 (#4): fixes for the 4 gaps found by the post-#3 verification pass
# that #3's static scan missed — all four used db.get() (a primary-key-only
# lookup) instead of a tenant-scoped select(), which #3's scan (select/
# update/delete only) didn't check for.
# ---------------------------------------------------------------------------

async def test_bank_voucher_does_not_mutate_foreign_tenant_balance(
    async_client: AsyncClient, db_session: AsyncSession, auth_headers, alt_tenant_headers, setup_tenant
):
    account_resp = await async_client.post(
        "/api/v1/omnichannel-billing/banks/accounts",
        headers=auth_headers,
        json={
            "bank_name": "Isolation Bank",
            "account_number": f"ISO-{uuid.uuid4().hex[:10]}",
            "ifsc_code": "ISOL0000001",
            "current_balance": 1000.0,
        },
    )
    assert account_resp.status_code == 201, account_resp.text
    bank_account_id = account_resp.json()["id"]

    # alt_tenant_headers' tenant creates a RECEIPT voucher against tenant
    # A's bank account. Before the fix, crud.create_bank_voucher used
    # db.get() (primary-key-only, no tenant filter) and would silently
    # credit tenant A's real balance from a voucher tenant A never made.
    voucher_resp = await async_client.post(
        "/api/v1/omnichannel-billing/banks/vouchers",
        headers=alt_tenant_headers,
        json={
            "bank_account_id": bank_account_id,
            "voucher_number": f"ISO-V-{uuid.uuid4().hex[:8]}",
            "voucher_type": "RECEIPT",
            "amount": 500.0,
        },
    )
    # The voucher record itself is still created (pre-existing business
    # logic: a voucher with no matching-and-owned bank account is a silent
    # no-op on the balance side, not an error — unchanged by this fix).
    assert voucher_resp.status_code == 201, voucher_resp.text

    from app.models.universal_banks import UniversalBankAccount

    check = await db_session.execute(
        select(UniversalBankAccount).where(UniversalBankAccount.id == bank_account_id)
    )
    account_after = check.scalar_one()
    assert float(account_after.current_balance) == 1000.0


async def test_credit_risk_score_rejects_foreign_tenant_customer(
    async_client: AsyncClient, auth_headers, alt_tenant_headers
):
    customer_resp = await async_client.post(
        "/api/v1/omnichannel-billing/customers/",
        headers=auth_headers,
        json={"name": "Isolation Credit Customer", "email": "credit-isolation@example.com"},
    )
    assert customer_resp.status_code == 201, customer_resp.text
    customer_id = customer_resp.json()["id"]

    # Before the fix, crud.calculate_credit_risk used db.get() (no tenant
    # filter) and would disclose tenant A's customer's credit_limit/name
    # to tenant B.
    foreign_resp = await async_client.get(
        f"/api/v1/omnichannel-billing/ai/risk-score/{customer_id}", headers=alt_tenant_headers
    )
    assert foreign_resp.status_code == 404

    owner_resp = await async_client.get(
        f"/api/v1/omnichannel-billing/ai/risk-score/{customer_id}", headers=auth_headers
    )
    assert owner_resp.status_code == 200


async def test_collection_status_rejects_foreign_tenant_customer(
    async_client: AsyncClient, auth_headers, alt_tenant_headers
):
    customer_resp = await async_client.post(
        "/api/v1/omnichannel-billing/customers/",
        headers=auth_headers,
        json={"name": "Isolation Collections Customer", "email": "collections-isolation@example.com"},
    )
    assert customer_resp.status_code == 201, customer_resp.text
    customer_id = customer_resp.json()["id"]

    # Before the fix, crud.get_collection_status used db.get() (no tenant
    # filter) and would disclose tenant A's customer's outstanding/credit
    # data to tenant B.
    foreign_resp = await async_client.get(
        f"/api/v1/omnichannel-billing/collections/status/{customer_id}", headers=alt_tenant_headers
    )
    assert foreign_resp.status_code == 404

    # Not asserting the owner's own request succeeds here: discovered
    # while writing this test that crud.get_collection_status has a
    # pre-existing, unrelated bug (references customer.company_name, but
    # the model's field is `name`) that 500s on ANY successful lookup,
    # same-tenant or not. Out of scope for a tenant-isolation fix ("do not
    # refactor unrelated code") — not fixed here, flagged for follow-up.
    # The property this test exists to prove — a foreign tenant is
    # rejected before reaching that broken line at all — already holds.


async def test_tax_invoice_rejects_foreign_tenant_customer(
    async_client: AsyncClient, auth_headers, alt_tenant_headers
):
    customer_resp = await async_client.post(
        "/api/v1/omnichannel-billing/customers/",
        headers=auth_headers,
        json={"name": "Isolation Invoice Customer", "email": "invoice-isolation@example.com"},
    )
    assert customer_resp.status_code == 201, customer_resp.text
    customer_id = customer_resp.json()["id"]

    # Before the fix, crud.create_tax_invoice had no ownership check on
    # customer_id at all; tenant B could create an invoice referencing
    # tenant A's customer.
    foreign_resp = await async_client.post(
        "/api/v1/omnichannel-billing/invoices/tax",
        headers=alt_tenant_headers,
        json={"customer_id": customer_id, "invoice_number": f"ISO-TAX-{uuid.uuid4().hex[:8]}", "items": []},
    )
    assert foreign_resp.status_code == 404

    owner_resp = await async_client.post(
        "/api/v1/omnichannel-billing/invoices/tax",
        headers=auth_headers,
        json={"customer_id": customer_id, "invoice_number": f"ISO-TAX-{uuid.uuid4().hex[:8]}", "items": []},
    )
    assert owner_resp.status_code == 201, owner_resp.text
