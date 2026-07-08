import pytest
from httpx import AsyncClient
from tests.conftest import create_mock_token

@pytest.mark.asyncio
async def test_unauthorized_access(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/migration/connectors")
    assert resp.status_code == 401 # Missing token

@pytest.mark.asyncio
async def test_tenant_isolation(async_client: AsyncClient, auth_headers):
    # Setup session as Tenant A (using auth_headers)
    import io
    import pandas as pd
    df = pd.DataFrame({"Name": ["Test"]})
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    upload_resp = await async_client.post(
        "/api/v1/migration/upload?entity_type=CUSTOMER",
        headers=auth_headers,
        files={"file": ("test.csv", csv_buffer, "text/csv")}
    )
    session_id = upload_resp.json()["id"]

    # Try to access as Tenant B
    tenant_b_id = "11111111-1111-1111-1111-111111111111"
    token_b = create_mock_token(
        user_id="user_b", 
        scopes=["*"], 
        tenant_id=tenant_b_id
    )
    headers_b = {"Authorization": f"Bearer {token_b}"}

    resp = await async_client.get(
        f"/api/v1/migration/execution/{session_id}/status",
        headers=headers_b
    )
    # Should be 403 because tenant_id doesn't match and the route returns 403
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_rbac_permissions(async_client: AsyncClient):
    # Role without migration access
    token = create_mock_token(
        user_id="user_viewer", 
        scopes=[], # Empty scopes for unauthorized access
        tenant_id="00000000-0000-0000-0000-000000000000"
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to trigger execute
    session_id = "00000000-0000-0000-0000-000000000000"
    resp = await async_client.post(
        f"/api/v1/migration/execution/{session_id}/execute",
        headers=headers
    )
    # Should be 403 Forbidden
    assert resp.status_code == 403
