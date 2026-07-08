from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.core.database import Base
from enum import Enum as pyEnum

class MigrationJobStatus(str, pyEnum):
    UPLOADED = 'UPLOADED'
    VALIDATING = 'VALIDATING'
    VALIDATION_FAILED = 'VALIDATION_FAILED'
    VALIDATION_SUCCESS = 'VALIDATION_SUCCESS'
    IMPORTING = 'IMPORTING'
    IMPORT_SUCCESS = 'IMPORT_SUCCESS'
    IMPORT_FAILED = 'IMPORT_FAILED'
    PARTIAL_SUCCESS = 'PARTIAL_SUCCESS'
    PAUSED = 'PAUSED'
    CANCELLING = 'CANCELLING'
    CANCELLED = 'CANCELLED'
    ROLLING_BACK = 'ROLLING_BACK'
    ROLLED_BACK = 'ROLLED_BACK'

class MigrationEntityType(str, pyEnum):
    CUSTOMER = 'CUSTOMER'
    VENDOR = 'VENDOR'
    ITEM = 'ITEM'
    CATEGORY = 'CATEGORY'
    UOM = 'UOM'
    WAREHOUSE = 'WAREHOUSE'
    BRANCH = 'BRANCH'
    CHART_OF_ACCOUNTS = 'CHART_OF_ACCOUNTS'
    OPENING_STOCK = 'OPENING_STOCK'
    OPENING_BALANCES = 'OPENING_BALANCES'

class MigrationSession(Base):
    __tablename__ = 'migration_sessions'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = mapped_column(String(50), nullable=False) # Changed from Enum for simplicity across DBs
    original_file_name = mapped_column(String(255), nullable=True)
    file_path = mapped_column(String(512), nullable=True)
    file_size_bytes = mapped_column(BigInteger, nullable=True)
    connector_id = mapped_column(UUID(as_uuid=True), ForeignKey("erp_connectors.id", ondelete="SET NULL"), nullable=True, index=True)
    status = mapped_column(String(50), default=MigrationJobStatus.UPLOADED, nullable=False)
    
    total_records = mapped_column(Integer, default=0, nullable=False)
    valid_records = mapped_column(Integer, default=0, nullable=False)
    invalid_records = mapped_column(Integer, default=0, nullable=False)
    imported_records = mapped_column(Integer, default=0, nullable=False)
    skipped_records = mapped_column(Integer, default=0, nullable=False)
    
    # Execution Tracking
    progress_percentage = mapped_column(Integer, default=0, nullable=False)
    processing_speed_mps = mapped_column(Float, default=0.0, nullable=False)
    estimated_remaining_time_sec = mapped_column(Integer, default=0, nullable=False)
    
    # AI & Metrics
    data_quality_score = mapped_column(Integer, nullable=True) # 0-100
    readiness_score = mapped_column(Integer, nullable=True) # 0-100
    
    mapping_config = mapped_column(JSONB, nullable=True) # E.g., {"Customer Name": "name", "Contact": "phone"}
    error_summary = mapped_column(Text, nullable=True)
    
    created_by = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class MigrationDataRecord(Base):
    """Stores the individual parsed rows for preview and validation purposes before import"""
    __tablename__ = 'migration_data_records'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = mapped_column(UUID(as_uuid=True), ForeignKey("migration_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = mapped_column(Integer, nullable=False)
    raw_data = mapped_column(JSONB, nullable=False) # The original row data as a dict
    mapped_data = mapped_column(JSONB, nullable=True) # Data mapped to target entity schema
    
    is_valid = mapped_column(Boolean, default=False, nullable=False)
    validation_errors = mapped_column(JSONB, nullable=True) # Array of error strings
    is_imported = mapped_column(Boolean, default=False, nullable=False)
    target_record_id = mapped_column(String(100), nullable=True) # The ID of the created entity in the real tables
    
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class MigrationMappingTemplate(Base):
    __tablename__ = 'migration_mapping_templates'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = mapped_column(String(50), nullable=False)
    name = mapped_column(String(100), nullable=False)
    mapping_config = mapped_column(JSONB, nullable=False)
    average_confidence = mapped_column(Integer, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class MigrationValidationLog(Base):
    __tablename__ = 'migration_validation_logs'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = mapped_column(UUID(as_uuid=True), ForeignKey("migration_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = mapped_column(Integer, nullable=False)
    rule_name = mapped_column(String(100), nullable=False)
    error_message = mapped_column(Text, nullable=False)
    suggestion = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class MigrationCleansingLog(Base):
    __tablename__ = 'migration_cleansing_logs'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = mapped_column(String(50), nullable=False)
    operation = mapped_column(String(50), nullable=False) # e.g. MERGE_DUPLICATE, KEEP_LATEST, NORMALIZE
    source_record_id = mapped_column(String(100), nullable=False)
    target_record_id = mapped_column(String(100), nullable=True)
    reason = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ERPConnector(Base):
    __tablename__ = 'erp_connectors'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = mapped_column(String(100), nullable=False)
    erp_type = mapped_column(String(50), nullable=False) # e.g., TALLY, SAP, NETSUITE
    credentials = mapped_column(JSONB, nullable=False) # Encrypted or stored credentials
    is_active = mapped_column(Boolean, default=True, nullable=False)
    last_sync_at = mapped_column(DateTime(timezone=True), nullable=True)
    health_status = mapped_column(String(50), default="UNKNOWN")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class ERPImportLog(Base):
    __tablename__ = 'erp_import_logs'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector_id = mapped_column(UUID(as_uuid=True), ForeignKey("erp_connectors.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = mapped_column(UUID(as_uuid=True), ForeignKey("migration_sessions.id", ondelete="SET NULL"), nullable=True)
    status = mapped_column(String(50), nullable=False) # e.g., SUCCESS, FAILED
    records_fetched = mapped_column(Integer, default=0)
    error_message = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class MigrationRollbackLog(Base):
    __tablename__ = 'migration_rollback_logs'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = mapped_column(UUID(as_uuid=True), ForeignKey("migration_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    status = mapped_column(String(50), nullable=False) # SUCCESS, FAILED, PARTIAL
    records_rolled_back = mapped_column(Integer, default=0, nullable=False)
    failed_rollbacks = mapped_column(Integer, default=0, nullable=False)
    error_summary = mapped_column(Text, nullable=True)
    created_by = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class MigrationReconciliationReport(Base):
    __tablename__ = 'migration_reconciliation_reports'
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = mapped_column(UUID(as_uuid=True), ForeignKey("migration_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    missing_records = mapped_column(Integer, default=0, nullable=False)
    duplicate_records = mapped_column(Integer, default=0, nullable=False)
    mismatched_records = mapped_column(Integer, default=0, nullable=False)
    import_accuracy_percentage = mapped_column(Float, default=100.0, nullable=False)
    discrepancy_json = mapped_column(JSONB, nullable=True) # Detailed mismatches
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
