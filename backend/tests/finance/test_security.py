import pytest
from httpx import AsyncClient
from uuid import UUID, uuid4

@pytest.mark.asyncio
async def test_tenant_isolation(async_client: AsyncClient, setup_tenant, auth_headers, alt_tenant_headers):
    """Ensure that Tenant B cannot access Tenant A's account groups."""
    # 1. Create an account group as Tenant A
    grp_resp = await async_client.post(
        "/api/v1/finance-core/account-groups",
        json={"tenant_id": str(setup_tenant.id), "code": "6000", "name": "Tenant A Equity", "category": "equity"},
        headers=auth_headers
    )
    assert grp_resp.status_code == 201

    # 2. Try to list account groups as Tenant B using alt_tenant_headers
    list_resp = await async_client.get("/api/v1/finance-core/account-groups", headers=alt_tenant_headers)
    assert list_resp.status_code == 200
    
    # 3. Assert Tenant B's list does not contain Tenant A's group
    data = list_resp.json()
    assert len(data) == 0 # Since Tenant B is brand new

@pytest.mark.asyncio
async def test_tenant_id_mismatch_rejection(async_client: AsyncClient, setup_tenant, auth_headers, alt_tenant_headers):
    """Ensure POST payloads cannot inject data for a different tenant"""
    tenant_b_id = alt_tenant_headers["X-Tenant-ID"]
    
    # User is acting as setup_tenant (Tenant A), but payload tries to write to tenant_b_id
    payload = {
        "tenant_id": tenant_b_id,
        "code": "7000", 
        "name": "Malicious Injection", 
        "category": "equity"
    }
    
    resp = await async_client.post("/api/v1/finance-core/account-groups", json=payload, headers=auth_headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Tenant ID mismatch"
