from datetime import datetime, timezone, timedelta
import pytest
from app.services.migration_ai import MigrationAIAssistant
from app.services.data_cleansing import DataCleansingEngine
from app.models.migration import MigrationEntityType

def test_ai_mapping_suggestions():
    # Test field mapping suggestions
    source_cols = ["Customer Name", "Email Address", "Phone No", "Random Header"]
    result = MigrationAIAssistant.suggest_field_mappings(source_cols, MigrationEntityType.CUSTOMER)
    
    assert result["entity_type"] == MigrationEntityType.CUSTOMER
    suggestions = result["suggestions"]
    assert len(suggestions) == 4
    
    # "Customer Name" -> "name"
    assert suggestions[0]["source_column"] == "Customer Name"
    assert suggestions[0]["suggested_target"] == "name"
    assert suggestions[0]["confidence_score"] > 60
    
    # "Email Address" -> "email"
    assert suggestions[1]["suggested_target"] == "email"
    
def test_data_cleansing_validation():
    errors = DataCleansingEngine.validate_format("email", "invalid_email.com")
    assert len(errors) == 1
    assert "Invalid email format" in errors[0]
    
    errors = DataCleansingEngine.validate_format("phone", "abc")
    assert len(errors) == 1
    assert "no digits found" in errors[0]
    
    errors = DataCleansingEngine.validate_format("unit_price", "$100.50")
    assert len(errors) == 0  # Should strip $ and validate float
    
def test_data_cleansing_duplicates():
    records = [
        {"name": "Acme Corp", "email": "info@acme.com", "phone": "1234567890"},
        {"name": "Acme Corporation", "email": "info@acme.com", "phone": "1234567890"},
        {"name": "Globex", "email": "hello@globex.com", "phone": "0987654321"}
    ]
    
    clusters = DataCleansingEngine.detect_duplicates(records, ["name", "email", "phone"], threshold=80)
    assert len(clusters) == 1
    assert clusters[0]["primary_index"] == 0
    assert clusters[0]["duplicate_indices"] == [1]

def test_data_transformations():
    data = {"Cust_Name": "acme", "Price": "$500"}
    rules = [
        {"type": "RENAME", "source": "Cust_Name", "target": "name"},
        {"type": "UPPERCASE", "field": "name"},
        {"type": "STRIP_CURRENCY", "field": "Price"}
    ]
    
    transformed = DataCleansingEngine.apply_transformations(data, rules)
    assert transformed.get("name") == "ACME"
    assert transformed.get("Price") == "500"
    assert "Cust_Name" not in transformed
