from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from uuid import UUID

@pytest.mark.asyncio
async def test_trial_balance(async_client: AsyncClient, setup_tenant, auth_headers):
    # This assumes that previous tests or fixtures have populated some ledger entries
    response = await async_client.get("/api/v1/finance-reports/trial-balance", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "lines" in data
    assert "total_debit" in data
    assert "total_credit" in data
    
    # Fundamental accounting rule: Total Debits must equal Total Credits on the TB
    assert data["total_debit"] == data["total_credit"]

@pytest.mark.asyncio
async def test_profit_and_loss(async_client: AsyncClient, setup_tenant, auth_headers):
    response = await async_client.get("/api/v1/finance-reports/profit-and-loss", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "revenue" in data
    assert "operating_expenses" in data
    assert "net_profit" in data

@pytest.mark.asyncio
async def test_balance_sheet(async_client: AsyncClient, setup_tenant, auth_headers):
    response = await async_client.get("/api/v1/finance-reports/balance-sheet", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "assets" in data
    assert "liabilities" in data
    assert "equity" in data
    
    # A = L + E (Checking that the report correctly structured it)
    total_assets = float(data.get("total_assets", 0.0))
    total_liabilities = float(data.get("total_liabilities", 0.0))
    total_equity = float(data.get("total_equity", 0.0))
    
    # Floating point comparison logic could go here
    assert total_assets == (total_liabilities + total_equity)

@pytest.mark.asyncio
async def test_cash_flow(async_client: AsyncClient, setup_tenant, auth_headers):
    response = await async_client.get("/api/v1/finance-reports/cash-flow", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "operating_activities" in data
    assert "net_cash_increase" in data
