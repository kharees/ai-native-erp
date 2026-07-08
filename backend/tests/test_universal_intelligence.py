import pytest
from httpx import AsyncClient

from tests.fixtures.inventory_fixtures import async_client, setup_tenant, auth_headers

pytestmark = pytest.mark.asyncio

async def test_ai_dashboard(async_client: AsyncClient, auth_headers: dict):
    # Test Dashboard retrieval
    res = await async_client.get("/api/v1/universal-intelligence/dashboard", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "health_score" in data
    assert "forecasts" in data
    assert "recommendations" in data

async def test_ai_copilot(async_client: AsyncClient, auth_headers: dict):
    # 1. Test Low Stock intent
    res1 = await async_client.post(
        "/api/v1/universal-intelligence/copilot/ask",
        json={"query": "Show me the low stock items"},
        headers=auth_headers
    )
    assert res1.status_code == 200
    assert res1.json()["intent"] == "FIND_LOW_STOCK"

    # 2. Test Expiry intent
    res2 = await async_client.post(
        "/api/v1/universal-intelligence/copilot/ask",
        json={"query": "What is going to expire next month?"},
        headers=auth_headers
    )
    assert res2.status_code == 200
    assert res2.json()["intent"] == "FIND_EXPIRY"
    
    # 3. Test Unknown/General intent
    res3 = await async_client.post(
        "/api/v1/universal-intelligence/copilot/ask",
        json={"query": "How are you today?"},
        headers=auth_headers
    )
    assert res3.status_code == 200
    assert res3.json()["intent"] == "GENERAL_INVENTORY_ASSIST"
