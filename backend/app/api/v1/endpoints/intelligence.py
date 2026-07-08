"""
app/api/v1/endpoints/intelligence.py
====================================
Router for AI Security & Identity Intelligence insights.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.intelligence import (
    RoleRecommendation,
    InactiveUserAlert,
    SecurityScoreResponse,
    NaturalLanguageQueryRequest,
    NaturalLanguageQueryResponse
)
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission
from app.services.ai_intelligence import IdentityAnalyzer, SecurityAnalyzer, AuditAnalyzer

router = APIRouter()

# ---------------------------------------------------------------------------
# Identity Intelligence
# ---------------------------------------------------------------------------
@router.get("/identity/inactive-users", response_model=List[InactiveUserAlert])
async def get_inactive_users(
    tenant_id: TenantIDDep,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Roles", action="Read"))
):
    """Detect users who have not logged in recently."""
    return await IdentityAnalyzer.get_inactive_users(db, tenant_id, days)

@router.get("/identity/recommendations", response_model=List[RoleRecommendation])
async def get_role_recommendations(
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="RBAC", feature="Roles", action="Read"))
):
    """Get AI recommendations for role assignments."""
    return await IdentityAnalyzer.get_role_recommendations(db, tenant_id)

# ---------------------------------------------------------------------------
# Security Intelligence
# ---------------------------------------------------------------------------
@router.get("/security/risk-scores", response_model=SecurityScoreResponse)
async def get_security_risk_score(
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="Audit", feature="Logs", action="Read"))
):
    """Calculate the real-time Organization Security Score."""
    return await SecurityAnalyzer.calculate_org_risk_score(db, tenant_id)

# ---------------------------------------------------------------------------
# Audit Intelligence
# ---------------------------------------------------------------------------
@router.post("/audit/natural-language-search", response_model=NaturalLanguageQueryResponse)
async def natural_language_search(
    request: NaturalLanguageQueryRequest,
    tenant_id: TenantIDDep,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(RequirePermission(module="Audit", feature="Logs", action="Read"))
):
    """Ask natural language questions about the audit ledger."""
    return await AuditAnalyzer.query_natural_language(db, tenant_id, request.query)
