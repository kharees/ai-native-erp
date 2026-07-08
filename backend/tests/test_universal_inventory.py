import pytest
from httpx import AsyncClient
import uuid

pytestmark = pytest.mark.asyncio

async def test_create_category(async_client: AsyncClient, auth_headers: dict):
    response = await async_client.post(
        "/api/v1/universal-inventory/categories",
        json={"code": "ELEC", "name": "Electronics", "description": "Electronic items"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "ELEC"
    return data["id"]

async def test_create_item(async_client: AsyncClient, auth_headers: dict, alt_tenant_headers: dict):
    cat_id = await test_create_category(async_client, auth_headers)
    
    response = await async_client.post(
        "/api/v1/universal-inventory/items",
        json={
            "item_code": "LAPTOP-01",
            "name": "High End Laptop",
            "category_id": cat_id,
            "is_active": True,
            "metadata_fields": {"type": "electronics"}
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    item = response.json()
    assert item["item_code"] == "LAPTOP-01"

    # Multi-Tenant Isolation Test
    alt_response = await async_client.get(
        "/api/v1/universal-inventory/items",
        headers=alt_tenant_headers
    )
    assert alt_response.status_code == 200
    assert len(alt_response.json()["items"]) == 0
