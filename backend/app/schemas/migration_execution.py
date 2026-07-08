from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from app.models.migration import MigrationJobStatus

class ExecutionStatusResponse(BaseModel):
    session_id: UUID
    status: MigrationJobStatus
    progress_percentage: int
    imported_records: int
    skipped_records: int
    failed_records: int
    processing_speed_mps: float
    estimated_remaining_time_sec: int
    message: str

class RollbackRequest(BaseModel):
    partial: bool = Field(default=False, description="If True, only rolls back failed/recent records based on parameters")
    record_ids: Optional[List[UUID]] = Field(default=None, description="Specific record IDs to rollback if partial=True")

class MigrationRollbackLogOut(BaseModel):
    id: UUID
    session_id: UUID
    status: str
    records_rolled_back: int
    failed_rollbacks: int
    error_summary: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ReconciliationReportOut(BaseModel):
    id: UUID
    session_id: UUID
    missing_records: int
    duplicate_records: int
    mismatched_records: int
    import_accuracy_percentage: float
    discrepancy_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
