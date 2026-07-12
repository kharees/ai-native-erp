import uuid
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from datetime import timezone, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.migration import ERPConnector, ERPImportLog, MigrationSession, MigrationJobStatus, MigrationEntityType, MigrationDataRecord

class ConnectorBase:
    def __init__(self, credentials: Dict[str, Any]):
        self.credentials = credentials

    async def authenticate(self) -> bool:
        """Authenticate with the ERP system."""
        raise NotImplementedError

    async def fetch_data(self, entity_type: str) -> List[Dict[str, Any]]:
        """Fetch data from the ERP system for a given entity type."""
        raise NotImplementedError

    async def test_connection(self) -> Dict[str, Any]:
        """Test the connection and return status."""
        try:
            success = await self.authenticate()
            return {
                "status": "SUCCESS" if success else "FAILED",
                "message": "Connection successful" if success else "Authentication failed",
                "timestamp": datetime.now(timezone.utc)
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "message": f"Connection error: {str(e)}",
                "timestamp": datetime.now(timezone.utc)
            }

class MockTallyConnector(ConnectorBase):
    async def authenticate(self) -> bool:
        await asyncio.sleep(0.5) # Simulate network delay
        return True
        
    async def fetch_data(self, entity_type: str) -> List[Dict[str, Any]]:
        await asyncio.sleep(1)
        if entity_type == MigrationEntityType.CUSTOMER:
            return [
                {"name": "Tally Corp", "email": "contact@tallycorp.com", "phone": "9876543210", "tally_id": "T001"},
                {"name": "Tally Retail", "email": "sales@tallyretail.com", "phone": "9876543211", "tally_id": "T002"},
            ]
        return []

class MockSAPConnector(ConnectorBase):
    async def authenticate(self) -> bool:
        await asyncio.sleep(0.5)
        return True
        
    async def fetch_data(self, entity_type: str) -> List[Dict[str, Any]]:
        await asyncio.sleep(1)
        if entity_type == MigrationEntityType.CUSTOMER:
            return [
                {"CUSTOMER_NAME": "SAP Enterprise", "EMAIL_ADDR": "admin@sapent.com", "PHONE_NUM": "1122334455", "SAP_ID": "S1001"},
            ]
        return []

class MockNetSuiteConnector(ConnectorBase):
    async def authenticate(self) -> bool:
        await asyncio.sleep(0.5)
        return True
        
    async def fetch_data(self, entity_type: str) -> List[Dict[str, Any]]:
        return []

# Factory for connectors
def get_connector(erp_type: str, credentials: Dict[str, Any]) -> ConnectorBase:
    connectors = {
        "TALLY": MockTallyConnector,
        "SAP": MockSAPConnector,
        "NETSUITE": MockNetSuiteConnector,
        # Default mock for others to avoid boilerplate
    }
    connector_class = connectors.get(erp_type, MockTallyConnector)
    return connector_class(credentials)

class ERPConnectorEngine:
    @staticmethod
    async def sync_connector(db: AsyncSession, tenant_id: uuid.UUID, connector_id: uuid.UUID, entity_type: MigrationEntityType) -> MigrationSession:
        """Triggers a manual sync from an ERP connector and creates a Migration Session."""
        # The current (only) caller — POST /erp-connectors/{id}/sync — already
        # verifies connector.tenant_id == tenant_id before reaching here, so
        # this filter isn't closing an active exploit today. It's the
        # defense-in-depth this function should have had regardless: nothing
        # about this signature previously stopped a future caller (another
        # endpoint, a background job, an agent tool) from syncing another
        # tenant's connector — using their stored ERP credentials — on behalf
        # of an unauthorized caller.
        stmt = select(ERPConnector).where(ERPConnector.id == connector_id, ERPConnector.tenant_id == tenant_id)
        connector = (await db.execute(stmt)).scalar_one_or_none()
        
        if not connector:
            raise ValueError("Connector not found")
            
        erp = get_connector(connector.erp_type, connector.credentials)
        
        # 1. Fetch data
        try:
            data = await erp.fetch_data(entity_type)
            status = "SUCCESS"
            error_message = None
        except Exception as e:
            status = "FAILED"
            data = []
            error_message = str(e)
            
        # 2. Log the import
        log = ERPImportLog(
            connector_id=connector.id,
            status=status,
            records_fetched=len(data),
            error_message=error_message
        )
        db.add(log)
        
        # Update connector status
        connector.last_sync_at = datetime.now(timezone.utc)
        connector.health_status = status
        
        if status == "FAILED" or not data:
            # Must be a real commit, not flush: we're about to raise, and the
            # request-scoped session (get_db/db_session) rolls back on any
            # exception. Without committing here first, the failure log and
            # connector health-status update this branch just wrote would be
            # wiped out by that rollback — the one thing we need to survive
            # a failed sync is the record that it failed.
            await db.commit()
            raise ValueError(f"Sync failed or no data returned: {error_message}")
            
        # 3. Create Migration Session directly from data
        session = MigrationSession(
            tenant_id=connector.tenant_id,
            entity_type=entity_type,
            original_file_name=f"Sync_{connector.erp_type}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json",
            connector_id=connector.id,
            file_size_bytes=len(str(data)),
            total_records=len(data),
            status=MigrationJobStatus.UPLOADED
        )
        db.add(session)
        await db.flush()
        
        log.session_id = session.id
        
        # 4. Create MigrationDataRecords
        records = []
        for index, row in enumerate(data):
            record = MigrationDataRecord(
                session_id=session.id,
                row_number=index + 1,
                raw_data=row
            )
            records.append(record)
            
        db.add_all(records)
        await db.flush()
        await db.refresh(session)

        return session
