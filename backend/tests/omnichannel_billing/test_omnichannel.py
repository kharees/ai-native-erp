import pytest
import uuid
from app.schemas.universal_pos import UniversalPOSHoldBillCreate
from app.schemas.universal_omnichannel import UniversalOrderChannelMappingCreate

def test_pos_hold_bill_jsonb():
    """Verify POS Hold Bill can store nested cart data"""
    session_id = uuid.uuid4()
    cart_payload = {
        "items": [
            {"product_id": str(uuid.uuid4()), "qty": 2, "price": 100.0},
            {"product_id": str(uuid.uuid4()), "qty": 1, "price": 50.0}
        ],
        "discount": 10.0
    }
    
    hold_bill = UniversalPOSHoldBillCreate(
        session_id=session_id,
        reference_name="Customer 1",
        cart_data=cart_payload
    )
    
    assert hold_bill.cart_data["discount"] == 10.0
    assert len(hold_bill.cart_data["items"]) == 2

def test_channel_mapping_schema():
    """Verify external order ID mapping abstract logic"""
    channel_id = uuid.uuid4()
    mapping = UniversalOrderChannelMappingCreate(
        channel_id=channel_id,
        external_order_id="SHOPIFY-99231",
        raw_payload={"source": "shopify", "total": 1200.0}
    )
    
    assert mapping.external_order_id == "SHOPIFY-99231"
    assert mapping.sync_status == "PENDING"
