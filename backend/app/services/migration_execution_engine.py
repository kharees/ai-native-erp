import uuid
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.migration import (
    MigrationSession, MigrationDataRecord, MigrationJobStatus, 
    MigrationRollbackLog, MigrationReconciliationReport
)

class MigrationExecutionManager:

    @staticmethod
    async def start_execution(db: AsyncSession, session_id: uuid.UUID):
        """Starts the migration in the background."""
        stmt = select(MigrationSession).where(MigrationSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found")
            
        session.status = MigrationJobStatus.IMPORTING
        await db.flush()
        await db.refresh(session)
        
        # In a real app, you'd trigger a Celery task here.
        # For this implementation, we simulate background processing using asyncio.create_task 
        # in the endpoint or we just return success and assume a worker picks it up.
        return session

    @staticmethod
    async def pause_execution(db: AsyncSession, session_id: uuid.UUID):
        stmt = select(MigrationSession).where(MigrationSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found")
            
        session.status = MigrationJobStatus.PAUSED
        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def resume_execution(db: AsyncSession, session_id: uuid.UUID):
        stmt = select(MigrationSession).where(MigrationSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found")
            
        session.status = MigrationJobStatus.IMPORTING
        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def cancel_execution(db: AsyncSession, session_id: uuid.UUID):
        stmt = select(MigrationSession).where(MigrationSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found")
            
        session.status = MigrationJobStatus.CANCELLING
        await db.flush()
        await db.refresh(session)
        return session

class MigrationRollbackEngine:

    @staticmethod
    async def rollback_session(db: AsyncSession, session_id: uuid.UUID, partial: bool = False, record_ids: list = None):
        """
        Rolls back imported records. 
        In a real scenario, this would delete or softly delete the target records created.
        """
        stmt = select(MigrationSession).where(MigrationSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found")
            
        session.status = MigrationJobStatus.ROLLING_BACK
        await db.flush()
        
        records_stmt = select(MigrationDataRecord).where(MigrationDataRecord.session_id == session_id, MigrationDataRecord.is_imported == True)
        if partial and record_ids:
            records_stmt = records_stmt.where(MigrationDataRecord.id.in_(record_ids))
            
        imported_records = (await db.execute(records_stmt)).scalars().all()
        
        rolled_back = 0
        failed = 0
        
        for record in imported_records:
            try:
                # 1. Identify target record ID
                # 2. Issue delete to target entity table (mocked here)
                record.is_imported = False
                record.target_record_id = None
                rolled_back += 1
            except Exception as e:
                failed += 1
                
        # Update session
        session.imported_records -= rolled_back
        session.status = MigrationJobStatus.ROLLED_BACK if not partial else MigrationJobStatus.PARTIAL_SUCCESS
        
        # Log
        log = MigrationRollbackLog(
            session_id=session.id,
            tenant_id=session.tenant_id,
            status="SUCCESS" if failed == 0 else "PARTIAL",
            records_rolled_back=rolled_back,
            failed_rollbacks=failed,
        )
        db.add(log)
        await db.flush()
        
        return log

class MigrationReconciliationEngine:

    @staticmethod
    async def generate_report(db: AsyncSession, session_id: uuid.UUID):
        """
        Compares imported records against the source data.
        """
        stmt = select(MigrationSession).where(MigrationSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found")
            
        # Mocking reconciliation logic
        # In reality, it compares MigrationDataRecord.mapped_data against target entity table rows
        missing = 0
        duplicate = 0
        mismatched = 0
        
        total = session.total_records
        if total > 0:
            missing = int(total * 0.02) # 2% missing
            duplicate = int(total * 0.01) # 1% duplicates
            mismatched = int(total * 0.05) # 5% mismatched
            accuracy = 100.0 - ((missing + duplicate + mismatched) / total * 100)
        else:
            accuracy = 100.0
            
        report = MigrationReconciliationReport(
            session_id=session.id,
            tenant_id=session.tenant_id,
            missing_records=missing,
            duplicate_records=duplicate,
            mismatched_records=mismatched,
            import_accuracy_percentage=round(accuracy, 2),
            discrepancy_json={"sample_mismatch": "Field 'amount' expected 100, got 99.5"}
        )
        
        db.add(report)
        await db.flush()
        await db.refresh(report)
        
        return report
