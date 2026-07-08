"""
app/services/ai_intelligence.py
===============================
Heuristic and Generative AI wrappers for Security & Identity Intelligence.
"""

import uuid
from typing import Any, Dict, List
from datetime import datetime
from datetime import timezone, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.models.users import UserProfile
from app.models.audit import TenantAuditLog
from app.models.sessions import TenantSession

class IdentityAnalyzer:
    """Provides recommendations on user roles and highlights anomalies (duplicates/inactive)."""
    
    @staticmethod
    async def get_inactive_users(db: AsyncSession, tenant_id: uuid.UUID, days_inactive: int = 30) -> List[Dict[str, Any]]:
        """Identify users who have not logged in recently."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_inactive)
        
        # We find users whose last active session is before cutoff_date OR who have no sessions
        stmt = select(UserProfile).where(
            UserProfile.tenant_id == tenant_id,
            UserProfile.is_active == True
        )
        
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        inactive_users = []
        for user in users:
            # Check their latest session
            sess_stmt = select(TenantSession.last_active_at).where(
                TenantSession.user_id == user.id
            ).order_by(desc(TenantSession.last_active_at)).limit(1)
            
            sess_result = await db.execute(sess_stmt)
            last_active = sess_result.scalar_one_or_none()
            
            if last_active is None or last_active < cutoff_date:
                inactive_users.append({
                    "user_id": str(user.id),
                    "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
                    "last_active": last_active.isoformat() if last_active else "Never",
                    "reason": f"Inactive for > {days_inactive} days"
                })
                
        return inactive_users

    @staticmethod
    async def get_role_recommendations(db: AsyncSession, tenant_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Mock Generative AI wrapper: Suggests roles based on department or missing roles."""
        return [
            {
                "user_id": "00000000-0000-0000-0000-000000000001",
                "email": "jane.doe@example.com",
                "recommended_role": "Finance Manager",
                "reason": "AI matched department 'Finance' and high organizational hierarchy.",
                "confidence": 0.92
            },
            {
                "user_id": "00000000-0000-0000-0000-000000000002",
                "email": "john.smith@example.com",
                "recommended_role": "Warehouse Staff",
                "reason": "User is assigned to 'Warehouse A' but lacks inventory permissions.",
                "confidence": 0.88
            }
        ]

class SecurityAnalyzer:
    """Calculates risk scores based on heuristics over audit and session data."""
    
    @staticmethod
    async def calculate_org_risk_score(db: AsyncSession, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """
        Calculate an overall security score (0-100, higher is better) based on recent incidents.
        """
        # Base score
        score = 100
        incidents = []
        
        # 1. Check for recent brute force (failed auths)
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        brute_force_stmt = select(func.count(TenantAuditLog.id)).where(
            TenantAuditLog.tenant_id == tenant_id,
            TenantAuditLog.action_type == "LOGIN_FAILED",
            TenantAuditLog.created_at >= cutoff
        )
        brute_force_count = (await db.execute(brute_force_stmt)).scalar() or 0
        
        if brute_force_count > 50:
            score -= 20
            incidents.append(f"High brute force activity ({brute_force_count} failed logins in 24h).")
        elif brute_force_count > 10:
            score -= 5
            
        # 2. Check for Privilege Escalations (many role assignments)
        privilege_stmt = select(func.count(TenantAuditLog.id)).where(
            TenantAuditLog.tenant_id == tenant_id,
            TenantAuditLog.action_type == "ROLE_ASSIGNED",
            TenantAuditLog.created_at >= cutoff
        )
        privilege_count = (await db.execute(privilege_stmt)).scalar() or 0
        
        if privilege_count > 10:
            score -= 15
            incidents.append(f"Unusual privilege escalation rate ({privilege_count} roles assigned in 24h).")
            
        # 3. Check for Impossible Travel / IP anomalies
        # Mock logic for heuristic IP delta checking
        incidents.append("Impossible travel detected for user 'admin@tenant.com' (US to CN in 2 hrs).")
        score -= 10
        
        return {
            "score": max(0, score),
            "trend": "decreasing" if score < 90 else "stable",
            "active_incidents": incidents
        }

class AuditAnalyzer:
    """Wraps Generative AI for Natural Language Audit Queries."""
    
    @staticmethod
    async def query_natural_language(db: AsyncSession, tenant_id: uuid.UUID, query: str) -> Dict[str, Any]:
        """
        Mock Generative LLM endpoint translating a natural language query into an audit summary.
        In a real scenario, this would send `query` and schema to OpenAI/Gemini to generate SQL.
        """
        return {
            "query": query,
            "ai_summary": "Based on the audit logs, Jane Smith (Admin) modified the 'Finance Manager' role permissions at 14:30 UTC yesterday, granting 'Delete' access on 'Invoices'.",
            "confidence": 0.95,
            "relevant_log_ids": ["c2f1a3...", "d4b2e1..."]
        }
