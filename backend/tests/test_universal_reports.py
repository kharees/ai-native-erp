from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient

from tests.fixtures.inventory_fixtures import async_client, setup_tenant, auth_headers

pytestmark = pytest.mark.asyncio

async def test_analytics_endpoints(async_client: AsyncClient, auth_headers: dict):
    # Test Summary Report
    sum_res = await async_client.get("/api/v1/universal-reports/summary", headers=auth_headers)
    assert sum_res.status_code == 200
    data = sum_res.json()
    assert "total_quantity" in data
    assert "total_value" in data

    # Test Aging Report
    aging_res = await async_client.get("/api/v1/universal-reports/aging", headers=auth_headers)
    assert aging_res.status_code == 200
    assert isinstance(aging_res.json(), list)
    
    # Test Aging CSV Export
    aging_csv = await async_client.get("/api/v1/universal-reports/aging?export=csv", headers=auth_headers)
    assert aging_csv.status_code == 200
    assert aging_csv.headers["content-type"] == "text/csv; charset=utf-8"
    assert "item_id,warehouse_id,quantity_on_hand" in aging_csv.text

    # Test ABC Analysis
    abc_res = await async_client.get("/api/v1/universal-reports/abc-analysis", headers=auth_headers)
    assert abc_res.status_code == 200
    assert isinstance(abc_res.json(), list)
