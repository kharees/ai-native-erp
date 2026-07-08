from datetime import datetime, timezone, timedelta
import pytest
import io
import pandas as pd
from httpx import AsyncClient
import uuid

@pytest.mark.asyncio
async def test_migration_upload_csv(async_client: AsyncClient, auth_headers):
    df = pd.DataFrame({
        "Customer Name": ["Acme Corp"],
        "Email": ["acme@example.com"],
        "Phone": ["555-1234"]
    })
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    files = {"file": ("test.csv", csv_buffer, "text/csv")}
    
    resp = await async_client.post(
        "/api/v1/migration/upload?entity_type=CUSTOMER",
        headers=auth_headers,
        files=files
    )
    assert resp.status_code == 201
    assert resp.json()["total_records"] == 1
    assert resp.json()["entity_type"] == "CUSTOMER"

@pytest.mark.asyncio
async def test_migration_upload_json(async_client: AsyncClient, auth_headers):
    json_data = b'[{"Customer Name": "JSON Corp", "Email": "json@test.com"}]'
    files = {"file": ("test.json", json_data, "application/json")}
    
    resp = await async_client.post(
        "/api/v1/migration/upload?entity_type=CUSTOMER",
        headers=auth_headers,
        files=files
    )
    assert resp.status_code == 201
    assert resp.json()["total_records"] == 1

@pytest.mark.asyncio
async def test_migration_upload_invalid_file(async_client: AsyncClient, auth_headers):
    # Uploading a txt file instead of csv/json/xlsx
    txt_data = b'random text'
    files = {"file": ("test.txt", txt_data, "text/plain")}
    
    resp = await async_client.post(
        "/api/v1/migration/upload?entity_type=CUSTOMER",
        headers=auth_headers,
        files=files
    )
    assert resp.status_code == 400
