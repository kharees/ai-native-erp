from datetime import datetime, timezone, timedelta
import pytest
import io
import pandas as pd
from httpx import AsyncClient
async def setup_session_helper(async_client, auth_headers):
    df = pd.DataFrame({"Name": ["Test"]})
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    upload_resp = await async_client.post(
        "/api/v1/migration/upload?entity_type=CUSTOMER",
        headers=auth_headers,
        files={"file": ("test.csv", csv_buffer, "text/csv")}
    )
    return upload_resp.json()["id"]

@pytest.mark.asyncio
async def test_execution_status(async_client: AsyncClient, auth_headers):
    setup_session = await setup_session_helper(async_client, auth_headers)
    resp = await async_client.get(
        f"/api/v1/migration/execution/{setup_session}/status",
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "status" in resp.json()

@pytest.mark.asyncio
async def test_execution_execute(async_client: AsyncClient, auth_headers):
    setup_session = await setup_session_helper(async_client, auth_headers)
    resp = await async_client.post(
        f"/api/v1/migration/execution/{setup_session}/execute",
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IMPORTING"

@pytest.mark.asyncio
async def test_execution_pause_resume(async_client: AsyncClient, auth_headers):
    setup_session = await setup_session_helper(async_client, auth_headers)
    pause_resp = await async_client.post(
        f"/api/v1/migration/execution/{setup_session}/pause",
        headers=auth_headers
    )
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "PAUSED"

    resume_resp = await async_client.post(
        f"/api/v1/migration/execution/{setup_session}/resume",
        headers=auth_headers
    )
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "IMPORTING"

@pytest.mark.asyncio
async def test_execution_cancel(async_client: AsyncClient, auth_headers):
    setup_session = await setup_session_helper(async_client, auth_headers)
    resp = await async_client.post(
        f"/api/v1/migration/execution/{setup_session}/cancel",
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLING"

@pytest.mark.asyncio
async def test_execution_rollback(async_client: AsyncClient, auth_headers):
    setup_session = await setup_session_helper(async_client, auth_headers)
    payload = {"partial": False}
    resp = await async_client.post(
        f"/api/v1/migration/execution/{setup_session}/rollback",
        headers=auth_headers,
        json=payload
    )
    assert resp.status_code == 200
    assert "records_rolled_back" in resp.json()

@pytest.mark.asyncio
async def test_execution_reconcile(async_client: AsyncClient, auth_headers):
    setup_session = await setup_session_helper(async_client, auth_headers)
    resp = await async_client.post(
        f"/api/v1/migration/execution/{setup_session}/reconcile",
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "import_accuracy_percentage" in resp.json()
