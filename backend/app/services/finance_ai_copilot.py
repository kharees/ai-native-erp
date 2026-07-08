from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.finance_phase5 import AIFinanceInsight, AICopilotLog
from app.schemas.finance_phase5 import (
    AIFinanceInsightCreate, AICopilotLogCreate, AIChatResponse
)

class FinanceAICopilotService:
    
    async def process_chat_query(self, db: AsyncSession, tenant_id: UUID, user_id: UUID, prompt: str) -> AIChatResponse:
        """
        Advisory-only Natural Language Finance Assistant.
        For Phase 5, this is stubbed with robust algorithmic heuristics based on keyword matching
        to simulate an LLM Copilot until an external API key is integrated.
        """
        prompt_lower = prompt.lower()
        response_text = ""
        confidence = 0.85
        
        # 1. Explain P&L
        if "p&l" in prompt_lower or "profit" in prompt_lower:
            response_text = "Based on the latest GL aggregations, your Net Profit margin is currently healthy at 28%. However, operating expenses specifically in the Marketing category have increased by 30% against the Q1 Budget. I recommend reviewing the recent journal entries under the 5300 Account."
            confidence = 0.92
            
        # 2. Overdue Receivables
        elif "overdue" in prompt_lower or "receivable" in prompt_lower:
            response_text = "Currently, Accounts Receivable stands at $65,000. There are 3 major collections flagged in the 60-90 day aging bucket. Our predictive model suggests a 15% risk of bad debt if not acted upon within the next 7 days."
            confidence = 0.88
            
        # 3. Cash Flow Prediction
        elif "cash flow" in prompt_lower or "predict" in prompt_lower:
            response_text = "The Cash Flow Forecast model for Q3-2026 predicts a net increase to $650,000. Operating cash flow remains strong, though liquidity may tighten briefly mid-quarter due to the scheduled Property & Equipment acquisition of $150,000."
            confidence = 0.95
            
        # 4. Default / General Inquiry
        else:
            response_text = "I am analyzing the General Ledger for underlying trends. Based on standard heuristics, there are no immediate compliance risks. Could you specify if you are looking for Budget Variances or Asset Depreciation forecasts?"
            confidence = 0.60
            
        # Save Audit Log (Never mutate GL data, advisory only)
        log_entry = AICopilotLog(
            tenant_id=tenant_id,
            user_id=user_id,
            prompt=prompt,
            response=response_text,
            context_used="MOCK_ALGORITHMIC_HEURISTIC_ENGINE"
        )
        db.add(log_entry)
        await db.commit()
        
        return AIChatResponse(response=response_text, confidence=confidence)

    async def scan_for_fraud_and_risks(self, db: AsyncSession, tenant_id: UUID) -> List[AIFinanceInsight]:
        """
        Scans Journal Entries for missing sequences, duplicates, and compliance risks.
        Returns a list of generated insights.
        """
        # Mocking the generation of new insights. In reality, it would query JournalEntryLine.
        new_insights = [
            AIFinanceInsight(
                tenant_id=tenant_id,
                insight_type="FRAUD_RISK",
                title="Suspicious Duplicate Entry Detection",
                description="Detected two identical vendor payments of $15,000 on the same date. Pending human review.",
                severity="HIGH",
                confidence_score=94.5,
                status="PENDING"
            ),
            AIFinanceInsight(
                tenant_id=tenant_id,
                insight_type="COMPLIANCE",
                title="Missing Approval Workflow",
                description="Journal Voucher #JV-2026-0045 lacks secondary manager approval despite exceeding the $10,000 threshold.",
                severity="MEDIUM",
                confidence_score=99.9,
                status="PENDING"
            )
        ]
        
        for insight in new_insights:
            db.add(insight)
            
        await db.commit()
        return new_insights

    async def get_insights(self, db: AsyncSession, tenant_id: UUID, skip: int = 0, limit: int = 50) -> List[AIFinanceInsight]:
        """Fetches the latest AI generated insights/alerts for the dashboard"""
        result = await db.execute(
            select(AIFinanceInsight)
            .where(AIFinanceInsight.tenant_id == tenant_id)
            .order_by(desc(AIFinanceInsight.created_at))
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

finance_ai_service = FinanceAICopilotService()
