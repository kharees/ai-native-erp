import uuid
from sqlalchemy import *
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class AIFinanceInsight(Base):
    __tablename__ = 'finance_ai_insights'
    
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    insight_type = mapped_column(String(50), nullable=False) # e.g. RISK, SUGGESTION, FORECAST, FRAUD
    title = mapped_column(String(255), nullable=False)
    description = mapped_column(Text, nullable=False)
    
    severity = mapped_column(String(20), nullable=False, default="LOW") # LOW, MEDIUM, HIGH, CRITICAL
    confidence_score = mapped_column(Numeric(5, 2), nullable=False, default=100.00) # Percentage
    
    # Reference to an entity this insight might be about (e.g. Journal Voucher ID)
    reference_id = mapped_column(String(100), nullable=True) 
    
    status = mapped_column(String(50), nullable=False, default="PENDING") # PENDING, APPROVED, REJECTED, RESOLVED
    
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AICopilotLog(Base):
    __tablename__ = 'finance_ai_copilot_logs'
    
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    prompt = mapped_column(Text, nullable=False)
    response = mapped_column(Text, nullable=False)
    context_used = mapped_column(Text, nullable=True) # What data did the AI look at to answer this?
    
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
