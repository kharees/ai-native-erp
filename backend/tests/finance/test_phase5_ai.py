from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from uuid import UUID

@pytest.mark.asyncio
async def test_cfo_copilot_chat(async_client: AsyncClient, setup_tenant, auth_headers):
    payload = {
        "prompt": "Explain the recent P&L and any expense increases."
    }
    resp = await async_client.post("/api/v1/finance-ai/chat", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "confidence" in data
    # The heuristic should match "p&l" and "expense"
    assert "Net Profit margin is currently healthy" in data["response"]
    assert data["confidence"] == 0.92

@pytest.mark.asyncio
async def test_trigger_fraud_scan_and_list_insights(async_client: AsyncClient, setup_tenant, auth_headers):
    resp = await async_client.post("/api/v1/finance-ai/scan-fraud", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2 # Should return the 2 mock insights
    assert data[0]["insight_type"] == "FRAUD_RISK"
    assert data[1]["insight_type"] == "COMPLIANCE"

    resp = await async_client.get("/api/v1/finance-ai/insights", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert data[0]["tenant_id"] == str(setup_tenant.id)
