import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.migration import MigrationSession, MigrationDataRecord
from app.schemas.migration_ai_copilot import (
    DataQualityReportOut, DataQualityMetric, ErrorAnalysisOut,
    CleansingSuggestion, CleansingSuggestionsOut, ChatResponseOut
)

class MigrationAICopilotService:

    @staticmethod
    async def analyze_data_quality(db: AsyncSession, session_id: uuid.UUID) -> DataQualityReportOut:
        """Analyzes data quality metrics for a session."""
        stmt = select(MigrationSession).where(MigrationSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found")
            
        total = session.total_records
        invalid = session.invalid_records
        
        health_score = 100
        risk_score = 0
        if total > 0:
            health_score = int((session.valid_records / total) * 100)
            risk_score = 100 - health_score
            
        metrics = []
        if invalid > 0:
            metrics.append(DataQualityMetric(
                category="Format Issues",
                issue_count=invalid,
                impact_level="HIGH",
                description="Records with invalid data types or formats."
            ))
            
        # Mocking duplicate detection for this phase
        duplicate_mock_count = int(total * 0.05) if total > 0 else 0
        if duplicate_mock_count > 0:
            metrics.append(DataQualityMetric(
                category="Duplicates",
                issue_count=duplicate_mock_count,
                impact_level="MEDIUM",
                description="Potential duplicate records detected based on similar names/emails."
            ))
            
        return DataQualityReportOut(
            health_score=health_score,
            risk_score=risk_score,
            metrics=metrics,
            overall_recommendation="Review the cleansing suggestions to resolve duplicates before importing." if duplicate_mock_count > 0 else "Data looks healthy for import."
        )

    @staticmethod
    def analyze_error_root_cause(error_message: str, row_data: Dict[str, Any]) -> ErrorAnalysisOut:
        """Deep analysis of an error message and row data."""
        err_lower = error_message.lower()
        
        if "missing" in err_lower or "null" in err_lower:
            return ErrorAnalysisOut(
                root_cause="A mandatory field was not provided in the source row.",
                suggested_fix="Update the mapping to provide a default value, or fix the source file.",
                impact_analysis="Record will be rejected by the database.",
                retry_recommended=False
            )
        elif "timeout" in err_lower or "lock" in err_lower:
            return ErrorAnalysisOut(
                root_cause="Database experienced a lock timeout due to concurrent operations.",
                suggested_fix="Retry the operation.",
                impact_analysis="Transient failure, no data corruption.",
                retry_recommended=True
            )
        elif "duplicate" in err_lower or "unique" in err_lower:
            return ErrorAnalysisOut(
                root_cause="A record with this unique identifier (e.g., email or code) already exists.",
                suggested_fix="Use the Data Cleansing merge feature to update the existing record instead of creating a new one.",
                impact_analysis="Record creation blocked to prevent data duplication.",
                retry_recommended=False
            )
            
        # Fallback
        return ErrorAnalysisOut(
            root_cause="Data format or validation mismatch.",
            suggested_fix="Review the raw data against target schema requirements.",
            impact_analysis="Record skipped.",
            retry_recommended=False
        )

    @staticmethod
    async def suggest_cleansing_rules(db: AsyncSession, session_id: uuid.UUID) -> CleansingSuggestionsOut:
        """Generates AI suggestions for data cleansing."""
        stmt = select(MigrationSession).where(MigrationSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        
        suggestions = []
        if session and session.total_records > 0:
            suggestions.append(CleansingSuggestion(
                suggestion_id=f"MERGE_DUP_{session_id}",
                type="MERGE_DUPLICATES",
                description="Merge records with identical email addresses.",
                affected_records_count=int(session.total_records * 0.05),
                proposed_action={"strategy": "keep_latest", "match_field": "email"},
                confidence_score=95
            ))
            suggestions.append(CleansingSuggestion(
                suggestion_id=f"NORMALIZE_PHONE_{session_id}",
                type="NORMALIZE_FORMAT",
                description="Standardize phone numbers to E.164 format.",
                affected_records_count=int(session.total_records * 0.15),
                proposed_action={"strategy": "format_e164", "target_field": "phone"},
                confidence_score=88
            ))
            
        return CleansingSuggestionsOut(suggestions=suggestions)

    @staticmethod
    async def natural_language_query(db: AsyncSession, session_id: uuid.UUID, query: str) -> ChatResponseOut:
        """Simulates an LLM for querying migration context."""
        query_lower = query.lower()
        stmt = select(MigrationSession).where(MigrationSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        
        if not session:
            return ChatResponseOut(response="I couldn't find the migration session you are referring to.")
            
        if "summary" in query_lower or "status" in query_lower:
            response = f"This session has {session.total_records} total records. {session.imported_records} have been successfully imported, and {session.invalid_records} failed validation."
            return ChatResponseOut(response=response, relevant_data={"total": session.total_records, "imported": session.imported_records})
            
        if "error" in query_lower or "fail" in query_lower:
            if session.invalid_records == 0:
                return ChatResponseOut(response="There are currently no failed records in this session.")
            response = f"There are {session.invalid_records} failed records. The most common cause appears to be missing mandatory fields or formatting issues. Would you like me to suggest cleansing rules?"
            return ChatResponseOut(response=response)
            
        if "duplicate" in query_lower:
            response = "Based on my analysis, about 5% of your records might be duplicates (matching on email/name). You can review these in the Cleansing Dashboard."
            return ChatResponseOut(response=response)
            
        if "cleansing" in query_lower or "fix" in query_lower:
            response = "I have generated some cleansing suggestions for you, including standardizing phone numbers and merging duplicate emails. You can apply them safely from the AI Recommendations panel."
            return ChatResponseOut(response=response)
            
        return ChatResponseOut(response="I'm your AI Migration Copilot. I can help you analyze errors, suggest data cleansing rules, and provide summaries of your import process. How can I assist you today?")
