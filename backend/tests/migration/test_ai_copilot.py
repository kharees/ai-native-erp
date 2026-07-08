import pytest
import io
import pandas as pd
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_ai_copilot_data_quality(async_client: AsyncClient, auth_headers):
    # Setup session
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

    # AI Quality
    resp = await async_client.get(
        f"/api/v1/migration/ai-copilot/{session_id}/data-quality",
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "health_score" in resp.json()
    assert "risk_score" in resp.json()

@pytest.mark.asyncio
async def test_ai_copilot_analyze_error(async_client: AsyncClient, auth_headers):
    # Real session
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
    
    payload = {
        "error_message": "Missing mandatory field: email",
        "row_data": {"name": "Test"}
    }
    resp = await async_client.post(
        f"/api/v1/migration/ai-copilot/{session_id}/analyze-error",
        headers=auth_headers,
        json=payload
    )
    assert resp.status_code == 200
    assert "root_cause" in resp.json()
    assert "mandatory" in resp.json()["root_cause"].lower()

@pytest.mark.asyncio
async def test_ai_copilot_chat(async_client: AsyncClient, auth_headers):
    # Real session for chat
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

    payload = {"query": "Why did migration fail?"}
    resp = await async_client.post(
        f"/api/v1/migration/ai-copilot/{session_id}/chat",
        headers=auth_headers,
        json=payload
    )
    assert resp.status_code == 200
    assert "response" in resp.json()

@pytest.mark.asyncio
async def test_ai_copilot_cleansing_suggestions(async_client: AsyncClient, auth_headers):
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

    resp = await async_client.get(
        f"/api/v1/migration/ai-copilot/{session_id}/cleansing-suggestions",
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "suggestions" in resp.json()
