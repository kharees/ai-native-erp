from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.migration import MigrationJobStatus, MigrationEntityType

# --- Session Responses ---
class MigrationSessionOut(BaseModel):
    id: UUID
    tenant_id: UUID
    entity_type: MigrationEntityType
    original_file_name: str
    file_size_bytes: int
    status: MigrationJobStatus
    total_records: int
    valid_records: int
    invalid_records: int
    imported_records: int
    mapping_config: Optional[Dict[str, Any]] = None
    data_quality_score: Optional[int] = None
    readiness_score: Optional[int] = None
    error_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Data Preview ---
class MigrationDataRecordOut(BaseModel):
    id: UUID
    row_number: int
    raw_data: Dict[str, Any]
    mapped_data: Optional[Dict[str, Any]] = None
    is_valid: bool
    validation_errors: Optional[List[str]] = None
    is_imported: bool
    
    model_config = ConfigDict(from_attributes=True)

class MigrationPreviewResponse(BaseModel):
    session: MigrationSessionOut
    records: List[MigrationDataRecordOut]
    total_count: int

# --- Action Payloads ---
class ValidateSessionPayload(BaseModel):
    mapping_config: Optional[Dict[str, str]] = Field(description="Map of Target Field -> Source Column Header")
    transformation_rules: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of rules to apply before mapping")

class AIMappingSuggestion(BaseModel):
    source_column: str
    suggested_target: Optional[str]
    confidence_score: int

class AIMappingResponse(BaseModel):
    entity_type: MigrationEntityType
    suggestions: List[AIMappingSuggestion]
    overall_confidence: int

class DuplicateClusterOut(BaseModel):
    primary_index: int
    duplicate_indices: List[int]
    
class CleansingResponse(BaseModel):
    duplicates_detected: int
    clusters: List[DuplicateClusterOut]
