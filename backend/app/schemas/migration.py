"""
app/schemas/migration.py
========================
Pydantic validation schemas for the Enterprise Data Migration Hub.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.migration import MigrationStatus


class DataMigrationLogBase(BaseModel):
    """
    Core attributes defining the uploaded migration file.
    """
    source_file_name: str = Field(..., max_length=255, description="Name of the uploaded source file")
    row_count_processed: int = Field(0, ge=0, description="Number of rows successfully processed")


class DataMigrationLogCreate(DataMigrationLogBase):
    """
    Parameters used when initializing a new migration batch job.
    """
    migration_status: MigrationStatus = Field(default=MigrationStatus.INITIALIZED)


class DataMigrationLogResponse(DataMigrationLogBase):
    """
    Response mapping representing the runtime execution tracking of the job.
    """
    id: UUID
    tenant_id: UUID
    migration_status: MigrationStatus
    error_log_dump: Optional[str] = None
    
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
