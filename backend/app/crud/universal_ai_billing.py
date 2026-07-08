import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_ai_billing import UniversalAIBillingLog, UniversalAIFraudAlert
from app.models.universal_customers import UniversalCustomer
from app.models.universal_invoices import UniversalTaxInvoice
from app.schemas.universal_ai_billing import (
    AICreditRiskScoreResponse, AISmartDraftRequest, AISmartDraftResponse
)

async def calculate_credit_risk(db: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID) -> AICreditRiskScoreResponse:
    customer = await db.get(UniversalCustomer, customer_id)
    if not customer:
        return None
    
    # Heuristic Mock Logic for Phase 6 Advisory Model
    stmt = select(func.count(UniversalTaxInvoice.id)).where(
        UniversalTaxInvoice.tenant_id == tenant_id,
        UniversalTaxInvoice.customer_id == customer_id,
        UniversalTaxInvoice.status == 'ISSUED'
    )
    unpaid_count = (await db.execute(stmt)).scalar_one_or_none() or 0

    risk_score = min(unpaid_count * 5, 100)
    
    category = "LOW"
    if risk_score > 75: category = "CRITICAL"
    elif risk_score > 50: category = "HIGH"
    elif risk_score > 25: category = "MEDIUM"

    log = UniversalAIBillingLog(
        tenant_id=tenant_id,
        customer_id=customer_id,
        inference_type="CREDIT_RISK",
        inference_payload={"score": risk_score, "category": category},
        confidence_score=0.92
    )
    db.add(log)
    await db.commit()

    return AICreditRiskScoreResponse(
        customer_id=customer_id,
        risk_score=risk_score,
        risk_category=category,
        delay_probability_percent=risk_score * 0.8,
        recommended_credit_limit=float(customer.credit_limit) if risk_score < 50 else float(customer.credit_limit) * 0.5,
        factors=["High number of unpaid invoices" if unpaid_count > 5 else "Healthy payment history"]
    )

async def generate_smart_draft(db: AsyncSession, tenant_id: uuid.UUID, payload: AISmartDraftRequest) -> AISmartDraftResponse:
    log = UniversalAIBillingLog(
        tenant_id=tenant_id,
        customer_id=payload.customer_id,
        inference_type="SMART_DRAFT",
        inference_payload={"requested_items": len(payload.partial_items)},
        confidence_score=0.88
    )
    db.add(log)
    await db.commit()

    return AISmartDraftResponse(
        suggested_products=[{"item_name": "Premium Bundle Add-on", "suggested_price": 99.99}],
        suggested_discounts=[{"type": "LOYALTY", "percentage": 5.0}],
        hsn_sac_recommendations={"item_1": "998311"},
        confidence_score=0.88
    )

async def scan_fraud_anomalies(db: AsyncSession, tenant_id: uuid.UUID):
    # Mock Fraud Scan returning open alerts
    stmt = select(UniversalAIFraudAlert).where(UniversalAIFraudAlert.tenant_id == tenant_id, UniversalAIFraudAlert.status == 'OPEN')
    return (await db.execute(stmt)).scalars().all()
