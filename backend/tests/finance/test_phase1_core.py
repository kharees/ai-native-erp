import pytest
from httpx import AsyncClient
from uuid import UUID
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_create_account_group(async_client: AsyncClient, setup_tenant, auth_headers):
    response = await async_client.post(
        "/api/v1/finance-core/account-groups",
        json={
            "tenant_id": str(setup_tenant.id),
            "code": "1000",
            "name": "Assets",
            "category": "asset"
        },
        headers=auth_headers
    )
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["code"] == "1000"
    assert data["category"] == "asset"
    return data["id"]

@pytest.mark.asyncio
async def test_create_account(async_client: AsyncClient, setup_tenant, auth_headers):
    # First create group
    grp_resp = await async_client.post(
        "/api/v1/finance-core/account-groups",
        json={"tenant_id": str(setup_tenant.id), "code": "2000", "name": "Liabilities", "category": "liability"},
        headers=auth_headers
    )
    assert grp_resp.status_code == 201, grp_resp.json()
    group_id = grp_resp.json()["id"]

    response = await async_client.post(
        "/api/v1/finance-core/accounts",
        json={
            "tenant_id": str(setup_tenant.id),
            "group_id": group_id,
            "account_code": "2100",
            "name": "Accounts Payable"
        },
        headers=auth_headers
    )
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["account_code"] == "2100"
    return data["id"]

@pytest.mark.asyncio
async def test_create_journal_voucher(async_client: AsyncClient, setup_tenant, auth_headers):
    # Create group
    grp_resp = await async_client.post(
        "/api/v1/finance-core/account-groups",
        json={"tenant_id": str(setup_tenant.id), "code": "5000", "name": "Expenses", "category": "expense"},
        headers=auth_headers
    )
    assert grp_resp.status_code == 201, grp_resp.json()
    group_id = grp_resp.json()["id"]

    # Create Accounts
    acc1_resp = await async_client.post(
        "/api/v1/finance-core/accounts",
        json={"tenant_id": str(setup_tenant.id), "group_id": group_id, "account_code": "5100", "name": "Office Expense"},
        headers=auth_headers
    )
    assert acc1_resp.status_code == 201
    acc1_id = acc1_resp.json()["id"]

    acc2_resp = await async_client.post(
        "/api/v1/finance-core/accounts",
        json={"tenant_id": str(setup_tenant.id), "group_id": group_id, "account_code": "1100", "name": "Cash"},
        headers=auth_headers
    )
    assert acc2_resp.status_code == 201
    acc2_id = acc2_resp.json()["id"]

    # Post Double Entry Journal (Debits == Credits)
    payload = {
        "tenant_id": str(setup_tenant.id),
        "voucher_number": "JV-001",
        "entry_date": datetime.now(timezone.utc).isoformat(),
        "reference": "REF-001",
        "description": "Office Supplies",
        "lines": [
            {"account_id": acc1_id, "debit": 500.0, "credit": 0.0, "description": "Bought pens"},
            {"account_id": acc2_id, "debit": 0.0, "credit": 500.0, "description": "Paid cash"}
        ]
    }
    jv_resp = await async_client.post("/api/v1/finance-core/journal-vouchers", json=payload, headers=auth_headers)
    assert jv_resp.status_code == 201, jv_resp.json()
    assert jv_resp.json()["voucher_number"] == "JV-001"

@pytest.mark.asyncio
async def test_double_entry_validation_fails(async_client: AsyncClient, setup_tenant, auth_headers):
    """Ensure that the system rejects unbalanced journal entries"""
    # Create an arbitrary group and account for testing failure
    grp_resp = await async_client.post(
        "/api/v1/finance-core/account-groups",
        json={"tenant_id": str(setup_tenant.id), "code": "9000", "name": "Misc", "category": "expense"},
        headers=auth_headers
    )
    assert grp_resp.status_code == 201
    
    acc_resp = await async_client.post(
        "/api/v1/finance-core/accounts",
        json={"tenant_id": str(setup_tenant.id), "group_id": grp_resp.json()["id"], "account_code": "9100", "name": "Misc Expense"},
        headers=auth_headers
    )
    assert acc_resp.status_code == 201
    acc_id = acc_resp.json()["id"]

    payload = {
        "tenant_id": str(setup_tenant.id),
        "voucher_number": "JV-FAIL-001",
        "entry_date": datetime.now(timezone.utc).isoformat(),
        "lines": [
            {"account_id": acc_id, "debit": 100.0, "credit": 0.0, "description": "Unbalanced Debit"}
            # Missing corresponding credit
        ]
    }
    response = await async_client.post("/api/v1/finance-core/journal-vouchers", json=payload, headers=auth_headers)
    # The service layer or API should reject unbalanced journals with a 400 Bad Request
    assert response.status_code == 400, response.json()
    assert "balance" in response.text.lower() or "unbalanced" in response.text.lower()
