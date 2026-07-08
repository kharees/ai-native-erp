"""
app/schemas/intelligence.py
===========================
Pydantic schemas for the AI Intelligence module.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class RoleRecommendation(BaseModel):
    user_id: str
    email: str
    recommended_role: str
    reason: str
    confidence: float

class InactiveUserAlert(BaseModel):
    user_id: str
    email: str
    name: str
    last_active: str
    reason: str

class SecurityScoreResponse(BaseModel):
    score: int
    trend: str
    active_incidents: List[str]

class NaturalLanguageQueryRequest(BaseModel):
    query: str = Field(..., description="The natural language question to ask the AI.")

class NaturalLanguageQueryResponse(BaseModel):
    query: str
    ai_summary: str
    confidence: float
    relevant_log_ids: List[str]
