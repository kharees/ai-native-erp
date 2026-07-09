from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
import uuid


pytestmark = pytest.mark.asyncio

async def test_batch_and_serial_tracking(async_client: AsyncClient, auth_headers: dict):
    # Setup Master Data
    cat_res = await async_client.post("/api/v1/universal-inventory/categories", json={"name": "Cat"}, headers=auth_headers)
    item_code = f"ITM-{uuid.uuid4()}"
    item_res = await async_client.post("/api/v1/universal-inventory/items", json={"item_code": item_code, "sku": item_code, "name": "Item", "category_id": cat_res.json()["id"]}, headers=auth_headers)
    item_id = item_res.json()["id"]
    
    wh_res = await async_client.post("/api/v1/universal-warehousing/warehouses", json={"code": f"WH-{uuid.uuid4()}", "name": "WH", "type": "main"}, headers=auth_headers)
    wh_id = wh_res.json()["id"]

    # 1. Create Batch Master
    batch_res = await async_client.post(
        "/api/v1/universal-tracking/batches",
        json={"item_id": item_id, "batch_number": "BATCH-001", "expiry_date": "2026-12-31"},
        headers=auth_headers
    )
    assert batch_res.status_code == 201
    batch_id = batch_res.json()["id"]

    # 2. Stock IN with Batch and Serials
    serials = [f"SN-{uuid.uuid4()}" for _ in range(3)]
    in_res = await async_client.post(
        "/api/v1/universal-warehousing/stock/transactions",
        json={
            "item_id": item_id,
            "warehouse_id": wh_id,
            "transaction_type": "IN",
            "reference_type": "GRN",
            "quantity": 3,
            "batch_id": batch_id,
            "serial_numbers": serials
        },
        headers=auth_headers
    )
    assert in_res.status_code == 201, in_res.json()

    # 3. Verify Serial Status is 'available'
    ser_res = await async_client.get(f"/api/v1/universal-tracking/serials?item_id={item_id}", headers=auth_headers)
    assert ser_res.status_code == 200
    for s in ser_res.json()["items"]:
        assert s["status"] == "available"
        assert s["warehouse_id"] == wh_id

    # 4. Stock OUT 1 Serial
    out_res = await async_client.post(
        "/api/v1/universal-warehousing/stock/transactions",
        json={
            "item_id": item_id,
            "warehouse_id": wh_id,
            "transaction_type": "OUT",
            "reference_type": "GI",
            "quantity": 1,
            "batch_id": batch_id,
            "serial_numbers": [serials[0]]
        },
        headers=auth_headers
    )
    assert out_res.status_code == 201, out_res.json()

    # 5. Verify Serial Status changed to 'dispatched'
    ser_res2 = await async_client.get(f"/api/v1/universal-tracking/serials?serial_number={serials[0]}", headers=auth_headers)
    assert ser_res2.json()["items"][0]["status"] == "dispatched"
    assert ser_res2.json()["items"][0]["warehouse_id"] is None
