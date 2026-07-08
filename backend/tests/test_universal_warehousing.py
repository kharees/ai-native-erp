from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
import uuid

# Import global fixtures
from tests.fixtures.inventory_fixtures import async_client, setup_tenant, auth_headers, alt_tenant_headers
from tests.test_universal_inventory import test_create_item

pytestmark = pytest.mark.asyncio

async def test_warehouse_and_stock_movement(async_client: AsyncClient, auth_headers: dict, alt_tenant_headers: dict):
    # 1. Create Warehouse
    wh_res = await async_client.post(
        "/api/v1/universal-warehousing/warehouses",
        json={"code": "WH-01", "name": "Main Warehouse", "type": "main"},
        headers=auth_headers
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]

    # 2. Create Item (reusing test)
    # The item creation requires an item, we can just hit the API
    cat_res = await async_client.post("/api/v1/universal-inventory/categories", json={"code": f"CAT-{uuid.uuid4()}", "name": "Cat"}, headers=auth_headers)
    item_res = await async_client.post("/api/v1/universal-inventory/items", json={"item_code": f"ITEM-{uuid.uuid4()}", "name": "Test Item", "category_id": cat_res.json()["id"]}, headers=auth_headers)
    item_id = item_res.json()["id"]

    # 3. Stock IN
    in_res = await async_client.post(
        "/api/v1/universal-warehousing/stock/movement",
        json={
            "item_id": item_id,
            "warehouse_id": wh_id,
            "transaction_type": "IN",
            "reference_type": "GRN",
            "quantity": 100,
            "metadata": {"unit_cost": 50.0}
        },
        headers=auth_headers
    )
    assert in_res.status_code == 200
    assert in_res.json()["quantity_on_hand"] == 100

    # 4. Stock OUT
    out_res = await async_client.post(
        "/api/v1/universal-warehousing/stock/movement",
        json={
            "item_id": item_id,
            "warehouse_id": wh_id,
            "transaction_type": "OUT",
            "reference_type": "GI",
            "quantity": 30
        },
        headers=auth_headers
    )
    assert out_res.status_code == 200
    assert out_res.json()["quantity_on_hand"] == 70

    # 5. Negative Stock Check (Should Fail)
    fail_res = await async_client.post(
        "/api/v1/universal-warehousing/stock/movement",
        json={
            "item_id": item_id,
            "warehouse_id": wh_id,
            "transaction_type": "OUT",
            "reference_type": "GI",
            "quantity": 100
        },
        headers=auth_headers
    )
    assert fail_res.status_code in [400, 409] # IntegrityError or ValueError

    # 6. Verify Ledger (Phase 3 Immutability Check)
    ledger_res = await async_client.get(f"/api/v1/universal-ledger/?item_id={item_id}", headers=auth_headers)
    assert ledger_res.status_code == 200
    ledger_items = ledger_res.json()["items"]
    assert len(ledger_items) == 2 # 1 IN, 1 OUT
    
    # Verify chronological quantity after
    assert ledger_items[-1]["quantity_before"] == 0
    assert ledger_items[-1]["movement_quantity"] == 100
    assert ledger_items[-1]["quantity_after"] == 100
    
    assert ledger_items[0]["quantity_before"] == 100
    assert ledger_items[0]["movement_quantity"] == -30
    assert ledger_items[0]["quantity_after"] == 70
