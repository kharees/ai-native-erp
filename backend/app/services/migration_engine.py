import os
import time
import uuid
import pandas as pd
from typing import List, Dict, Any, Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import json
import math

from app.models.migration import MigrationSession, MigrationDataRecord, MigrationJobStatus, MigrationEntityType
from app.crud import universal_customers, crud_finance_core, inventory, crud_finance_phase2
from app.schemas.universal_customers import UniversalCustomerCreate
from app.schemas.finance_core import AccountCreate
from app.schemas.finance_phase2 import APVendorCreate

UPLOAD_DIR = "/tmp/migration_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Sessions with more valid records than this run the import in the request
# (existing, contract-preserving synchronous behavior — tests and typical
# small imports rely on getting the final status back in the response).
# Above it, POST /import enqueues a Celery task (app/tasks/migration_tasks.py)
# and returns immediately with status IMPORTING; the caller polls
# GET /migration/execution/{id}/status. This is the real fix for #27: a
# large legacy import (tens of thousands of rows) no longer runs inside one
# HTTP request/response cycle and risks a gateway timeout.
IMPORT_ASYNC_THRESHOLD = 500

# Records processed per commit. Committing per-chunk rather than once at the
# very end means a crash mid-import only loses the current in-flight chunk —
# already-committed records keep is_imported=True, so resuming (re-running
# the same session_id's import) only reprocesses the remainder, since the
# record query below always filters is_imported == False.
CHUNK_SIZE = 200


async def _import_one_record(db: AsyncSession, session: MigrationSession, record: "MigrationDataRecord") -> bool:
    """Creates the target entity for one migration record. Returns True on
    success; on failure, marks the record and returns False rather than
    raising, so one bad row doesn't abort the whole chunk."""
    try:
        if session.entity_type == MigrationEntityType.CUSTOMER:
            create_schema = UniversalCustomerCreate(
                tenant_id=session.tenant_id,
                name=record.mapped_data.get('name'),
                email=record.mapped_data.get('email'),
                phone=record.mapped_data.get('phone')
            )
            created = await universal_customers.create_customer(db, session.tenant_id, create_schema)
            record.target_record_id = str(created.id)
        elif session.entity_type == MigrationEntityType.VENDOR:
            create_schema = APVendorCreate(
                tenant_id=session.tenant_id,
                name=record.mapped_data.get('name'),
                email=record.mapped_data.get('email'),
                phone=record.mapped_data.get('phone')
            )
            created = await crud_finance_phase2.finance_phase2.create_ap_vendor(db, obj_in=create_schema)
            record.target_record_id = str(created.id)
        elif session.entity_type == MigrationEntityType.CHART_OF_ACCOUNTS:
            create_schema = AccountCreate(
                tenant_id=session.tenant_id,
                account_code=record.mapped_data.get('account_code'),
                name=record.mapped_data.get('name'),
                account_type=record.mapped_data.get('account_type', 'Asset'),
                normal_balance=record.mapped_data.get('normal_balance', 'Debit')
            )
            created = await crud_finance_core.finance_core.create_account(db, obj_in=create_schema)
            record.target_record_id = str(created.id)
        elif session.entity_type == MigrationEntityType.ITEM:
            created = await inventory.create_inventory_item(db, session.tenant_id, record.mapped_data)
            record.target_record_id = str(created.id)

        record.is_imported = True
        return True
    except Exception as e:
        record.is_imported = False
        record.validation_errors = (record.validation_errors or []) + [f"Import Error: {str(e)}"]
        return False


async def execute_import_chunked(db: AsyncSession, session: MigrationSession, chunk_size: int = CHUNK_SIZE) -> MigrationSession:
    """
    Processes valid, not-yet-imported records for `session` in chunks,
    committing (checkpointing) after each one and updating
    progress_percentage / processing_speed_mps / estimated_remaining_time_sec
    so GET /migration/execution/{id}/status reflects real progress instead
    of jumping straight from 0% to 100%. Used both for the synchronous
    small-session path and inside the Celery task for large sessions — the
    only difference is which caller awaits it and whether the caller can
    wait for the return value before responding to its own client.

    Deliberate exception to the flush-only unit-of-work convention used
    everywhere else in app/crud and app/services: a bulk import is not one
    atomic business operation, it's a resumable batch job, and per-chunk
    commits are the checkpointing mechanism that makes a crash mid-import
    (or a Celery retry) resume instead of restart. See
    app/tasks/migration_tasks.py's retry-semantics docstring.
    """
    records_stmt = select(MigrationDataRecord).where(
        MigrationDataRecord.session_id == session.id,
        MigrationDataRecord.is_valid == True,
        MigrationDataRecord.is_imported == False
    ).order_by(MigrationDataRecord.row_number)
    valid_records = list((await db.execute(records_stmt)).scalars().all())

    total_to_process = len(valid_records)
    processed = 0
    t_start = time.monotonic()

    for chunk_start in range(0, total_to_process, chunk_size):
        chunk = valid_records[chunk_start: chunk_start + chunk_size]
        chunk_imported = 0
        for record in chunk:
            if await _import_one_record(db, session, record):
                chunk_imported += 1

        session.imported_records += chunk_imported
        processed += len(chunk)
        session.progress_percentage = int((processed / total_to_process) * 100) if total_to_process else 100
        elapsed = max(time.monotonic() - t_start, 0.001)
        session.processing_speed_mps = round(processed / elapsed, 2)
        remaining = total_to_process - processed
        session.estimated_remaining_time_sec = int(remaining / (processed / elapsed)) if processed > 0 else 0

        await db.commit()
        await db.refresh(session)

    if session.imported_records >= session.total_records:
        session.status = MigrationJobStatus.IMPORT_SUCCESS
    else:
        session.status = MigrationJobStatus.PARTIAL_SUCCESS
    await db.commit()
    await db.refresh(session)
    return session

class MigrationEngine:
    
    @staticmethod
    async def initialize_session(db: AsyncSession, tenant_id: uuid.UUID, entity_type: MigrationEntityType, file: UploadFile) -> MigrationSession:
        if not file.filename.endswith(('.csv', '.xlsx', '.json')):
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
            
        # Parse file to count rows and extract raw data
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file.filename.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            elif file.filename.endswith('.json'):
                df = pd.read_json(file_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
            
        # Clean NaN values
        df = df.replace({float('nan'): None})
        
        session = MigrationSession(
            tenant_id=tenant_id,
            entity_type=entity_type,
            original_file_name=file.filename,
            file_path=file_path,
            file_size_bytes=len(content),
            total_records=len(df),
            status=MigrationJobStatus.UPLOADED
        )
        db.add(session)
        await db.flush()
        
        # Create Data Records
        records = []
        for index, row in df.iterrows():
            record = MigrationDataRecord(
                session_id=session.id,
                row_number=index + 1,
                raw_data=row.to_dict()
            )
            records.append(record)
            
        db.add_all(records)
        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def validate_session(db: AsyncSession, tenant_id: uuid.UUID, session_id: uuid.UUID, mapping_config: Optional[Dict[str, str]] = None, transformation_rules: Optional[List[Dict[str, Any]]] = None) -> MigrationSession:
        from app.services.data_cleansing import DataCleansingEngine
        from app.services.migration_ai import MigrationAIAssistant
        from app.models.migration import MigrationValidationLog

        stmt = select(MigrationSession).where(MigrationSession.id == session_id, MigrationSession.tenant_id == tenant_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        session.status = MigrationJobStatus.VALIDATING
        if mapping_config:
            session.mapping_config = mapping_config
        await db.flush()

        # Fetch all records
        records_stmt = select(MigrationDataRecord).where(MigrationDataRecord.session_id == session_id)
        records_result = await db.execute(records_stmt)
        records = records_result.scalars().all()
        
        valid_count = 0
        invalid_count = 0
        validation_logs = []
        
        for record in records:
            errors = []
            
            # 1. Transformations
            transformed_raw = record.raw_data
            if transformation_rules:
                transformed_raw = DataCleansingEngine.apply_transformations(transformed_raw, transformation_rules)
            
            # 2. Mapping
            mapped = transformed_raw
            if mapping_config:
                mapped = {}
                for target_field, source_field in mapping_config.items():
                    if source_field in transformed_raw:
                        mapped[target_field] = transformed_raw[source_field]
            
            record.mapped_data = mapped
            
            # 3. Entity-specific Required Validation
            if session.entity_type == MigrationEntityType.CUSTOMER:
                if not mapped.get('name'):
                    errors.append("Missing mandatory field: 'name'")
            elif session.entity_type == MigrationEntityType.CHART_OF_ACCOUNTS:
                if not mapped.get('name'):
                    errors.append("Missing mandatory field: 'name'")
                if not mapped.get('account_code'):
                    errors.append("Missing mandatory field: 'account_code'")
                    
            # 4. Format Validation (Data Cleansing Engine)
            for k, v in mapped.items():
                format_errors = DataCleansingEngine.validate_format(k, v)
                errors.extend(format_errors)
                
            if errors:
                record.is_valid = False
                record.validation_errors = errors
                invalid_count += 1
                
                # Generate AI Explanation
                for err in errors:
                    ai_suggestion = MigrationAIAssistant.explain_validation_error(err, mapped)
                    log = MigrationValidationLog(
                        session_id=session.id,
                        row_number=record.row_number,
                        rule_name="AI_VALIDATOR",
                        error_message=err,
                        suggestion=ai_suggestion
                    )
                    validation_logs.append(log)
            else:
                record.is_valid = True
                record.validation_errors = []
                valid_count += 1
                
        session.valid_records = valid_count
        session.invalid_records = invalid_count
        session.status = MigrationJobStatus.VALIDATION_SUCCESS if invalid_count == 0 else MigrationJobStatus.VALIDATION_FAILED
        
        total = session.total_records
        session.data_quality_score = int((valid_count / total) * 100) if total > 0 else 0
        session.readiness_score = session.data_quality_score
        
        if validation_logs:
            db.add_all(validation_logs)

        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def import_session(db: AsyncSession, tenant_id: uuid.UUID, session_id: uuid.UUID) -> MigrationSession:
        stmt = select(MigrationSession).where(MigrationSession.id == session_id, MigrationSession.tenant_id == tenant_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status not in [MigrationJobStatus.VALIDATION_SUCCESS, MigrationJobStatus.VALIDATION_FAILED]:
            raise HTTPException(status_code=400, detail="Session must be validated before import")

        session.status = MigrationJobStatus.IMPORTING
        # A real commit (not flush) is required here, not just request-scoped
        # unit-of-work hygiene: below, run_migration_import.delay() hands this
        # session_id to a Celery worker running in a separate process with its
        # own DB connection. flush() only makes rows visible on *this*
        # connection/transaction — the worker cannot see them until this
        # transaction actually commits.
        await db.commit()
        await db.refresh(session)

        if session.total_records > IMPORT_ASYNC_THRESHOLD:
            # Large import: enqueue and return immediately. The client polls
            # GET /migration/execution/{id}/status for progress instead of
            # holding one HTTP request open for the whole import.
            from app.tasks.migration_tasks import run_migration_import
            run_migration_import.delay(str(session.id), str(session.tenant_id))
            return session

        return await execute_import_chunked(db, session)
