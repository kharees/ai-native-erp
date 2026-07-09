from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
import uuid

pytestmark = pytest.mark.asyncio

async def test_create_category(async_client: AsyncClient, auth_headers: dict):
    # UniversalCategory (model + schema) has no `code` field - only name/description/
    # parent_id/is_active. Confirmed against app/models/universal_inventory.py and
    # app/schemas/universal_inventory.py; the frontend categories page doesn't
    # reference a code either. Extra request fields are ignored by Pydantic.
    response = await async_client.post(
        "/api/v1/universal-inventory/categories",
        json={"name": "Electronics", "description": "Electronic items"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Electronics"
    return data["id"]

async def test_create_item(async_client: AsyncClient, auth_headers: dict, alt_tenant_headers: dict):
    cat_id = await test_create_category(async_client, auth_headers)
    
    response = await async_client.post(
        "/api/v1/universal-inventory/items",
        json={
            "item_code": "LAPTOP-01",
            "sku": "LAPTOP-01-SKU",
            "name": "High End Laptop",
            "category_id": cat_id,
            "is_active": True,
            "attributes": {"type": "electronics"}
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
