from datetime import datetime, timezone, timedelta
import pytest
import io
import uuid
import pandas as pd
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_migration_upload(async_client: AsyncClient, setup_tenant, auth_headers):
    # Create sample CSV
    df = pd.DataFrame({
        "Customer Name": ["Acme Corp", "Globex"],
        "Email": ["acme@example.com", "info@globex.com"],
        "Phone": ["555-1234", "555-5678"]
    })
    
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    files = {"file": ("test_customers.csv", csv_buffer, "text/csv")}
    
    # Upload
    resp = await async_client.post(
        "/api/v1/migration/upload?entity_type=CUSTOMER",
        headers=auth_headers,
        files=files
    )
    
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_records"] == 2
    session_id = data["id"]
    
    # Validate
    val_payload = {
        "mapping_config": {
            "name": "Customer Name",
            "email": "Email",
            "phone": "Phone"
        }
    }
    resp = await async_client.post(
        f"/api/v1/migration/{session_id}/validate",
        headers=auth_headers,
        json=val_payload
    )
    assert resp.status_code == 200
    assert resp.json()["valid_records"] == 2
    
    # Preview
    resp = await async_client.get(
        f"/api/v1/migration/{session_id}/preview",
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["total_count"] == 2
    
    # Import
    resp = await async_client.post(
        f"/api/v1/migration/{session_id}/import",
        headers=auth_headers
    )
    print("IMPORT RESP", resp.json())
    assert resp.status_code == 200
    
    resp_prev = await async_client.get(
        f"/api/v1/migration/{session_id}/preview",
        headers=auth_headers
    )
    print("PREVIEW AFTER IMPORT", resp_prev.json())
    
    assert resp.json()["status"] == "IMPORT_SUCCESS"
    assert resp.json()["imported_records"] == 2
