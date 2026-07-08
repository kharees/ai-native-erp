import pytest
import uuid
from app.schemas.universal_ai_billing import (
    AISmartDraftRequest, AIFraudAlertBase
)

def test_smart_draft_request_schema():
    """Verify AI Smart Draft input validation"""
    req = AISmartDraftRequest(
        customer_id=uuid.uuid4(),
        partial_items=[{"name": "Widget A"}]
    )
    assert len(req.partial_items) == 1

def test_fraud_alert_schema():
    """Verify AI Fraud Alert structured payload"""
    alert = AIFraudAlertBase(
        alert_type="DUPLICATE_INVOICE",
        severity="HIGH",
        alert_details="Invoice #123 matches Invoice #122 exactly in amount and items for same day."
    )
    
    assert alert.alert_type == "DUPLICATE_INVOICE"
    assert alert.severity == "HIGH"
    assert alert.status == "OPEN"
