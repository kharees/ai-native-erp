from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_erp_connector(async_client: AsyncClient, auth_headers):
    payload = {
        "name": "Test Tally",
        "erp_type": "TALLY",
        "credentials": {"username": "admin", "password": "password"}
    }
    resp = await async_client.post(
        "/api/v1/migration/connectors",
        headers=auth_headers,
        json=payload
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["name"] == "Test Tally"

@pytest.mark.asyncio
async def test_get_erp_connectors(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/migration/connectors",
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_test_connector_connection(async_client: AsyncClient, auth_headers):
    payload = {
        "name": "Test SAP",
        "erp_type": "SAP",
        "credentials": {"host": "localhost"}
    }
    create_resp = await async_client.post(
        "/api/v1/migration/connectors",
        headers=auth_headers,
        json=payload
    )
    connector_id = create_resp.json()["id"]

    test_resp = await async_client.post(
        f"/api/v1/migration/connectors/{connector_id}/test",
        headers=auth_headers
    )
    assert test_resp.status_code == 200
    assert test_resp.json()["status"] == "SUCCESS"

@pytest.mark.asyncio
async def test_trigger_connector_sync(async_client: AsyncClient, auth_headers):
    payload = {
        "name": "Test SAP",
        "erp_type": "SAP",
        "credentials": {}
    }
    create_resp = await async_client.post(
        "/api/v1/migration/connectors",
        headers=auth_headers,
        json=payload
    )
    connector_id = create_resp.json()["id"]

    sync_resp = await async_client.post(
        f"/api/v1/migration/connectors/{connector_id}/sync?entity_type=CUSTOMER",
        headers=auth_headers
    )
    assert sync_resp.status_code == 200
    assert sync_resp.json()["status"] == "UPLOADED"
