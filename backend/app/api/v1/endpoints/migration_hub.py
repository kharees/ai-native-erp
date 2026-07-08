from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
from app.core.database import get_db
from app.middleware.rbac import RequirePermission
from app.models.migration import MigrationEntityType, MigrationDataRecord, MigrationSession
from app.schemas.migration_hub import (
    ValidateSessionPayload, MigrationSessionOut,
    MigrationPreviewResponse, AIMappingResponse, CleansingResponse,
    MigrationDataRecordOut
)
from app.services.migration_engine import MigrationEngine
from sqlalchemy import select, func
from app.services.audit import AuditLogger

router = APIRouter()

def get_tenant_id(request: Request) -> uuid.UUID:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant context missing")
    try:
        return uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")


@router.post("/upload", response_model=MigrationSessionOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Migration", "System", "Execute"))])
async def upload_migration_file(
    request: Request,
    entity_type: MigrationEntityType = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    session = await MigrationEngine.initialize_session(db, tenant_id, entity_type, file)
    await AuditLogger.log_action(db=db, request=request, action_category="MIGRATION", action_type="UPLOAD_FILE", resource_id=str(session.id))
    return session

@router.post("/{session_id}/validate", response_model=MigrationSessionOut)
async def validate_migration_session(
    session_id: uuid.UUID,
    payload: ValidateSessionPayload,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """
    Validates data mapping and applies transformations.
    """
    return await MigrationEngine.validate_session(
        db, 
        session_id, 
        mapping_config=payload.mapping_config, 
        transformation_rules=payload.transformation_rules
    )

@router.get("/{session_id}/ai-mapping", response_model=AIMappingResponse)
async def ai_suggest_mapping(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """
    Returns AI-suggested field mappings for uploaded raw data.
    """
    from app.services.migration_ai import MigrationAIAssistant
    
    stmt = select(MigrationSession).where(MigrationSession.id == session_id, MigrationSession.tenant_id == tenant_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Migration session not found")
        
    # Pick a random record to get headers
    record_stmt = select(MigrationDataRecord.raw_data).where(MigrationDataRecord.session_id == session_id).limit(1)
    record_result = await db.execute(record_stmt)
    sample_raw = record_result.scalar_one_or_none()
    
    if not sample_raw:
        raise HTTPException(status_code=400, detail="No data available for mapping")
        
    source_columns = list(sample_raw.keys())
    return MigrationAIAssistant.suggest_field_mappings(source_columns, session.entity_type)

@router.get("/{session_id}/cleansing", response_model=CleansingResponse)
async def analyze_cleansing_rules(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """
    Analyzes mapped data for duplicates and returns duplicate clusters.
    """
    from app.services.data_cleansing import DataCleansingEngine
    
    stmt = select(MigrationDataRecord).where(MigrationDataRecord.session_id == session_id)
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    # Extract mapped data dictionaries
    mapped_records = [r.mapped_data for r in records if r.mapped_data]
    
    match_fields = ["name", "email", "phone"] # Configurable based on entity later
    clusters = DataCleansingEngine.detect_duplicates(mapped_records, match_fields)
    
    return {
        "duplicates_detected": sum(len(c["duplicate_indices"]) for c in clusters),
        "clusters": clusters
    }

@router.get("/{session_id}/preview", response_model=MigrationPreviewResponse, dependencies=[Depends(RequirePermission("Migration", "System", "Execute"))])
async def preview_migration_session(
    request: Request,
    session_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    only_invalid: bool = False,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    
    stmt = select(MigrationSession).where(MigrationSession.id == session_id, MigrationSession.tenant_id == tenant_id)
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
        
    records_stmt = select(MigrationDataRecord).where(MigrationDataRecord.session_id == session_id)
    if only_invalid:
        records_stmt = records_stmt.where(MigrationDataRecord.is_valid == False)
        
    # Count total
    count_stmt = select(func.count()).select_from(records_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()
    
    records_stmt = records_stmt.order_by(MigrationDataRecord.row_number).offset(skip).limit(limit)
    records = (await db.execute(records_stmt)).scalars().all()
    
    return MigrationPreviewResponse(
        session=MigrationSessionOut.model_validate(session),
        records=[MigrationDataRecordOut.model_validate(r) for r in records],
        total_count=total
    )

@router.post("/{session_id}/import", response_model=MigrationSessionOut, dependencies=[Depends(RequirePermission("Migration", "System", "Execute"))])
async def run_import_session(
    request: Request,
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    stmt = select(MigrationSession).where(MigrationSession.id == session_id, MigrationSession.tenant_id == tenant_id)
    if not (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
        
    session = await MigrationEngine.import_session(db, session_id)
    await AuditLogger.log_action(db=db, request=request, action_category="MIGRATION", action_type="IMPORT_DATA", resource_id=str(session.id))
    return session
