from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class DataQualityMetric(BaseModel):
    category: str
    issue_count: int
    impact_level: str # HIGH, MEDIUM, LOW
    description: str

class DataQualityReportOut(BaseModel):
    health_score: int # 0-100
    risk_score: int # 0-100
    metrics: List[DataQualityMetric]
    overall_recommendation: str

class ErrorAnalysisRequest(BaseModel):
    error_message: str
    row_data: Dict[str, Any]

class ErrorAnalysisOut(BaseModel):
    root_cause: str
    suggested_fix: str
    impact_analysis: str
    retry_recommended: bool

class CleansingSuggestion(BaseModel):
    suggestion_id: str
    type: str # MERGE_DUPLICATES, NORMALIZE_FORMAT
    description: str
    affected_records_count: int
    proposed_action: Dict[str, Any]
    confidence_score: int

class CleansingSuggestionsOut(BaseModel):
    suggestions: List[CleansingSuggestion]

class ChatRequest(BaseModel):
    query: str

class ChatResponseOut(BaseModel):
    response: str
    relevant_data: Optional[Dict[str, Any]] = None
