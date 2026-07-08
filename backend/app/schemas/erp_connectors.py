from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

class ERPConnectorBase(BaseModel):
    name: str = Field(..., description="Name of the connector, e.g., 'Main Tally Server'")
    erp_type: str = Field(..., description="Type of ERP, e.g., TALLY, SAP, NETSUITE")
    credentials: Dict[str, Any] = Field(..., description="Connection credentials")
    is_active: Optional[bool] = True

class ERPConnectorCreate(ERPConnectorBase):
    pass

class ERPConnectorUpdate(BaseModel):
    name: Optional[str] = None
    erp_type: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class ERPConnectorOut(ERPConnectorBase):
    id: UUID
    tenant_id: UUID
    last_sync_at: Optional[datetime] = None
    health_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ERPImportLogOut(BaseModel):
    id: UUID
    connector_id: UUID
    session_id: Optional[UUID] = None
    status: str
    records_fetched: int
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConnectorHealthCheckOut(BaseModel):
    status: str
    message: str
    timestamp: datetime
