from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from sqlalchemy import select

from app.core.database import get_db
from app.middleware.rbac import RequirePermission
from app.models.migration import ERPConnector, ERPImportLog, MigrationEntityType
from app.schemas.erp_connectors import ERPConnectorCreate, ERPConnectorUpdate, ERPConnectorOut, ERPImportLogOut, ConnectorHealthCheckOut
from app.schemas.migration_hub import MigrationSessionOut
from app.services.erp_connector_engine import ERPConnectorEngine, get_connector
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

@router.get("", response_model=List[ERPConnectorOut])
async def list_connectors(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    stmt = select(ERPConnector).where(ERPConnector.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("", response_model=ERPConnectorOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequirePermission("Migration", "System", "Configure"))])
async def create_connector(
    request: Request,
    payload: ERPConnectorCreate,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    connector = ERPConnector(
        tenant_id=tenant_id,
        name=payload.name,
        erp_type=payload.erp_type,
        credentials=payload.credentials,
        is_active=payload.is_active
    )
    db.add(connector)
    await db.flush()
    await db.refresh(connector)
    await AuditLogger.log_action(db=db, request=request, action_category="ERP_CONNECTOR", action_type="CREATE", resource_id=str(connector.id))
    return connector

@router.get("/{connector_id}", response_model=ERPConnectorOut)
async def get_connector_endpoint(
    request: Request,
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    stmt = select(ERPConnector).where(ERPConnector.id == connector_id, ERPConnector.tenant_id == tenant_id)
    connector = (await db.execute(stmt)).scalar_one_or_none()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector

@router.put("/{connector_id}", response_model=ERPConnectorOut, dependencies=[Depends(RequirePermission("Migration", "System", "Configure"))])
async def update_connector(
    request: Request,
    connector_id: uuid.UUID,
    payload: ERPConnectorUpdate,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    stmt = select(ERPConnector).where(ERPConnector.id == connector_id, ERPConnector.tenant_id == tenant_id)
    connector = (await db.execute(stmt)).scalar_one_or_none()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    if payload.name is not None:
        connector.name = payload.name
    if payload.erp_type is not None:
        connector.erp_type = payload.erp_type
    if payload.credentials is not None:
        connector.credentials = payload.credentials
    if payload.is_active is not None:
        connector.is_active = payload.is_active
        
    await db.flush()
    await db.refresh(connector)
    await AuditLogger.log_action(db=db, request=request, action_category="ERP_CONNECTOR", action_type="UPDATE", resource_id=str(connector.id))
    return connector

@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, dependencies=[Depends(RequirePermission("Migration", "System", "Configure"))])
async def delete_connector(
    request: Request,
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    stmt = select(ERPConnector).where(ERPConnector.id == connector_id, ERPConnector.tenant_id == tenant_id)
    connector = (await db.execute(stmt)).scalar_one_or_none()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    await db.delete(connector)
    await db.flush()
    await AuditLogger.log_action(db=db, request=request, action_category="ERP_CONNECTOR", action_type="DELETE", resource_id=str(connector_id))

@router.post("/{connector_id}/test", response_model=ConnectorHealthCheckOut)
async def test_connector(
    request: Request,
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    stmt = select(ERPConnector).where(ERPConnector.id == connector_id, ERPConnector.tenant_id == tenant_id)
    connector = (await db.execute(stmt)).scalar_one_or_none()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    erp = get_connector(connector.erp_type, connector.credentials)
    result = await erp.test_connection()
    
    connector.health_status = result["status"]
    await db.flush()
    
    return result

@router.post("/{connector_id}/sync", response_model=MigrationSessionOut, dependencies=[Depends(RequirePermission("Migration", "System", "Execute"))])
async def sync_connector(
    request: Request,
    connector_id: uuid.UUID,
    entity_type: MigrationEntityType,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    stmt = select(ERPConnector).where(ERPConnector.id == connector_id, ERPConnector.tenant_id == tenant_id)
    connector = (await db.execute(stmt)).scalar_one_or_none()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    if not connector.is_active:
        raise HTTPException(status_code=400, detail="Connector is not active")
        
    try:
        session = await ERPConnectorEngine.sync_connector(db, connector.id, entity_type)
        await AuditLogger.log_action(db=db, request=request, action_category="ERP_CONNECTOR", action_type="SYNC", resource_id=str(connector.id))
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{connector_id}/logs", response_model=List[ERPImportLogOut])
async def get_connector_logs(
    request: Request,
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant_id = get_tenant_id(request)
    # Verify connector belongs to tenant
    stmt_conn = select(ERPConnector).where(ERPConnector.id == connector_id, ERPConnector.tenant_id == tenant_id)
    if not (await db.execute(stmt_conn)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Connector not found")
        
    stmt = select(ERPImportLog).where(ERPImportLog.connector_id == connector_id).order_by(ERPImportLog.created_at.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()
