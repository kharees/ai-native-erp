import uuid
import pytest
from httpx import AsyncClient
from uuid import UUID
from datetime import datetime
from sqlalchemy import insert

from app.models.universal_customers import UniversalCustomer


async def _make_customer(db_session, tenant_id, name="Test Customer"):
    customer_id = uuid.uuid4()
    await db_session.execute(
        insert(UniversalCustomer).values(id=customer_id, tenant_id=tenant_id, name=name)
    )
    await db_session.commit()
    return customer_id


@pytest.mark.asyncio
async def test_create_ar_ledger_and_list(async_client: AsyncClient, setup_tenant, auth_headers, db_session):
    customer_id = await _make_customer(db_session, setup_tenant.id)
    payload = {
        "tenant_id": str(setup_tenant.id),
        "customer_id": str(customer_id),
        "outstanding_amount": 1500.0,
        "credit_limit": 5000.0,
        "is_bad_debt": False
    }
    response = await async_client.post("/api/v1/finance-ar-ap/ar/ledgers", json=payload, headers=auth_headers)
    assert response.status_code == 201

    # List
    list_resp = await async_client.get("/api/v1/finance-ar-ap/ar/ledgers", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) > 0

@pytest.mark.asyncio
async def test_ar_collections_and_receipts(async_client: AsyncClient, setup_tenant, auth_headers, db_session):
    customer_id = await _make_customer(db_session, setup_tenant.id)
    coll_payload = {
        "tenant_id": str(setup_tenant.id),
        "customer_id": str(customer_id),
        "status": "PROMISED_TO_PAY",
        "notes": "Will pay next week"
    }
    c_resp = await async_client.post("/api/v1/finance-ar-ap/ar/collections", json=coll_payload, headers=auth_headers)
    assert c_resp.status_code == 201

    cl_resp = await async_client.get("/api/v1/finance-ar-ap/ar/collections", headers=auth_headers)
    assert cl_resp.status_code == 200

    rect_payload = {
        "tenant_id": str(setup_tenant.id),
        "customer_id": str(customer_id),
        "receipt_number": "REC-001",
        "amount": 500.0,
        "payment_mode": "CASH",
        "unallocated_amount": 500.0
    }
    r_resp = await async_client.post("/api/v1/finance-ar-ap/ar/receipts", json=rect_payload, headers=auth_headers)
    assert r_resp.status_code == 201

    rl_resp = await async_client.get("/api/v1/finance-ar-ap/ar/receipts", headers=auth_headers)
    assert rl_resp.status_code == 200

@pytest.mark.asyncio
async def test_ap_vendor_bills_payments(async_client: AsyncClient, setup_tenant, auth_headers):
    # Need to create account first for vendor
    grp_resp = await async_client.post(
        "/api/v1/finance-core/account-groups",
        json={"tenant_id": str(setup_tenant.id), "code": "2000", "name": "Liabilities", "category": "liability"},
        headers=auth_headers
    )
    group_id = grp_resp.json()["id"]

    acc_resp = await async_client.post(
        "/api/v1/finance-core/accounts",
        json={"tenant_id": str(setup_tenant.id), "group_id": group_id, "account_code": "2100", "name": "Accounts Payable"},
        headers=auth_headers
    )
    acc_id = acc_resp.json()["id"]

    payload = {
        "tenant_id": str(setup_tenant.id),
        "name": "Acme Corp",
        "email": "acme@example.com",
    }
    response = await async_client.post("/api/v1/finance-ar-ap/ap/vendors", json=payload, headers=auth_headers)
    assert response.status_code == 201
    vendor_id = response.json()["id"]

    v_list = await async_client.get("/api/v1/finance-ar-ap/ap/vendors", headers=auth_headers)
    assert v_list.status_code == 200

    bill_payload = {
        "tenant_id": str(setup_tenant.id),
        "vendor_id": vendor_id,
        "bill_number": "BILL-001",
        "amount": 1000.0,
        "due_date": datetime.now().isoformat()
    }
    b_resp = await async_client.post("/api/v1/finance-ar-ap/ap/bills", json=bill_payload, headers=auth_headers)
    assert b_resp.status_code == 201

    bl_resp = await async_client.get("/api/v1/finance-ar-ap/ap/bills", headers=auth_headers)
    assert bl_resp.status_code == 200

    pay_payload = {
        "tenant_id": str(setup_tenant.id),
        "vendor_id": vendor_id,
        "payment_number": "PAY-001",
        "amount": 1000.0,
        "payment_mode": "BANK_TRANSFER",
        "unallocated_amount": 0.0
    }
    p_resp = await async_client.post("/api/v1/finance-ar-ap/ap/payments", json=pay_payload, headers=auth_headers)
    assert p_resp.status_code == 201

    pl_resp = await async_client.get("/api/v1/finance-ar-ap/ap/payments", headers=auth_headers)
    assert pl_resp.status_code == 200

@pytest.mark.asyncio
async def test_bank_and_expense(async_client: AsyncClient, setup_tenant, auth_headers, db_session):
    from app.models.universal_banks import UniversalBankAccount

    bank_account_id = uuid.uuid4()
    await db_session.execute(
        insert(UniversalBankAccount).values(
            id=bank_account_id, tenant_id=setup_tenant.id, bank_name="Test Bank",
            account_number="ACC-001", ifsc_code="TEST0001"
        )
    )
    await db_session.commit()

    br_payload = {
        "tenant_id": str(setup_tenant.id),
        "bank_account_id": str(bank_account_id),
        "statement_date": datetime.now().isoformat(),
        "statement_balance": 5000.0,
        "system_balance": 5000.0
    }
    br_resp = await async_client.post("/api/v1/finance-ar-ap/banking/reconciliations", json=br_payload, headers=auth_headers)
    assert br_resp.status_code == 201

    brl_resp = await async_client.get("/api/v1/finance-ar-ap/banking/reconciliations", headers=auth_headers)
    assert brl_resp.status_code == 200

    ca_payload = {
        "tenant_id": str(setup_tenant.id),
        "name": "Petty Cash",
        "is_petty_cash": True,
        "balance": 1000.0
    }
    ca_resp = await async_client.post("/api/v1/finance-ar-ap/cash-accounts", json=ca_payload, headers=auth_headers)
    assert ca_resp.status_code == 201

    cal_resp = await async_client.get("/api/v1/finance-ar-ap/cash-accounts", headers=auth_headers)
    assert cal_resp.status_code == 200

    ec_payload = {
        "tenant_id": str(setup_tenant.id),
        "name": "Travel",
        "description": "Travel expenses"
    }
    ec_resp = await async_client.post("/api/v1/finance-ar-ap/expenses/categories", json=ec_payload, headers=auth_headers)
    assert ec_resp.status_code == 201
    cat_id = ec_resp.json()["id"]

    ecl_resp = await async_client.get("/api/v1/finance-ar-ap/expenses/categories", headers=auth_headers)
    assert ecl_resp.status_code == 200

    ex_payload = {
        "tenant_id": str(setup_tenant.id),
        # user_id is force-overwritten server-side from the JWT identity; value here is irrelevant.
        "user_id": str(uuid.uuid4()),
        "category_id": cat_id,
        "amount": 150.0,
        "status": "SUBMITTED"
    }
    ex_resp = await async_client.post("/api/v1/finance-ar-ap/expenses/claims", json=ex_payload, headers=auth_headers)
    assert ex_resp.status_code == 201

    exl_resp = await async_client.get("/api/v1/finance-ar-ap/expenses/claims", headers=auth_headers)
    assert exl_resp.status_code == 200
