from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from uuid import UUID

@pytest.mark.asyncio
async def test_create_asset_category_and_asset(async_client: AsyncClient, setup_tenant, auth_headers):
    # Category
    cat_payload = {
        "tenant_id": str(setup_tenant.id),
        "name": "Vehicles",
        "depreciation_method": "SLM",
        "default_depreciation_rate": 20.00
    }
    cat_resp = await async_client.post("/api/v1/finance-assets/assets/categories", json=cat_payload, headers=auth_headers)
    assert cat_resp.status_code == 201
    cat_id = cat_resp.json()["id"]

    # Asset
    asset_payload = {
        "tenant_id": str(setup_tenant.id),
        "category_id": cat_id,
        "asset_code": "V-001",
        "name": "Delivery Truck",
        "acquisition_date": "2026-01-01T00:00:00Z",
        "acquisition_cost": 50000.0,
        "salvage_value": 5000.0,
        "useful_life_years": 5,
        "current_value": 50000.0,
        "depreciation_method": "SLM",
        "depreciation_rate": 20.0
    }
    asset_resp = await async_client.post("/api/v1/finance-assets/assets", json=asset_payload, headers=auth_headers)
    assert asset_resp.status_code == 201
    assert asset_resp.json()["current_value"] == "50000.00"

    asset_list = await async_client.get("/api/v1/finance-assets/assets", headers=auth_headers)
    assert asset_list.status_code == 200

    # Trigger the engine
    resp = await async_client.post("/api/v1/finance-assets/assets/run-depreciation", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "assets_depreciated" in data
    assert float(data["total_depreciation_amount"]) == 750.0

@pytest.mark.asyncio
async def test_cost_and_profit_centers(async_client: AsyncClient, setup_tenant, auth_headers):
    cc_payload = {
        "tenant_id": str(setup_tenant.id),
        "name": "IT Department",
        "code": "CC-IT",
        "description": "IT operations"
    }
    cc_resp = await async_client.post("/api/v1/finance-assets/cost-centers", json=cc_payload, headers=auth_headers)
    assert cc_resp.status_code == 201

    ccl_resp = await async_client.get("/api/v1/finance-assets/cost-centers", headers=auth_headers)
    assert ccl_resp.status_code == 200

    pc_payload = {
        "tenant_id": str(setup_tenant.id),
        "name": "Retail Branch 1",
        "code": "PC-R1",
        "description": "Retail branch in NYC"
    }
    pc_resp = await async_client.post("/api/v1/finance-assets/profit-centers", json=pc_payload, headers=auth_headers)
    assert pc_resp.status_code == 201

    pcl_resp = await async_client.get("/api/v1/finance-assets/profit-centers", headers=auth_headers)
    assert pcl_resp.status_code == 200

@pytest.mark.asyncio
async def test_create_budget(async_client: AsyncClient, setup_tenant, auth_headers):
    payload = {
        "tenant_id": str(setup_tenant.id),
        "name": "FY26 OPEX",
        "fiscal_year": "2026",
        "period_type": "ANNUAL",
        "lines": []
    }
    resp = await async_client.post("/api/v1/finance-assets/budgets", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "FY26 OPEX"

    list_resp = await async_client.get("/api/v1/finance-assets/budgets", headers=auth_headers)
    assert list_resp.status_code == 200

@pytest.mark.asyncio
async def test_create_forecast(async_client: AsyncClient, setup_tenant, auth_headers):
    payload = {
        "tenant_id": str(setup_tenant.id),
        "name": "Q3 Revenue Target",
        "target_period": "Q3-2026",
        "forecast_type": "REVENUE",
        "predicted_amount": 1500000.00
    }
    resp = await async_client.post("/api/v1/finance-assets/forecasts", json=payload, headers=auth_headers)
    assert resp.status_code == 201

    list_resp = await async_client.get("/api/v1/finance-assets/forecasts", headers=auth_headers)
    assert list_resp.status_code == 200
