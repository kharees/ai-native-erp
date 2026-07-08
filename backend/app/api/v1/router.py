"""
app/api/v1/router.py
====================
Top-level API v1 router aggregator.

All module routers are registered here and mounted under /api/v1 in main.py.
Add new module routers to this file as they are created.

Phase 3 addition
----------------
    The ``endpoints.inventory`` router provides the Multi-Tenant Handloom
    Inventory Control Ledger Pipelines Engine surface — three async endpoints
    purpose-built for saree inventory ingestion, tenancy-scoped catalog
    listing, and advanced JSONB attribute filtering.
"""

from fastapi import APIRouter

from app.api.v1 import inventory
from app.api.v1.endpoints import inventory as handloom_inventory

api_router = APIRouter()

# ---------------------------------------------------------------------------
# Phase 1/2 — General ERP inventory module — /api/v1/inventory
# ---------------------------------------------------------------------------
api_router.include_router(
    inventory.router,
    prefix="/inventory",
    tags=["Inventory"],
)

# ---------------------------------------------------------------------------
# Phase 3 — Multi-Tenant Handloom Inventory Control Ledger Pipelines Engine
#            Mounted under /api/v1/inventory/saree to avoid route collision
#            with the general CRUD router above.  Specialised saree domain
#            endpoints:
#              POST   /api/v1/inventory/saree/              — ingest node
#              GET    /api/v1/inventory/saree/              — catalog listing
#              GET    /api/v1/inventory/saree/filter-attributes/ — JSONB filter
# ---------------------------------------------------------------------------
api_router.include_router(
    handloom_inventory.router,
    prefix="/inventory/saree",
    tags=["Multi-Tenant Handloom Inventory Control Ledger Pipelines Engine"],
)

from app.api.v1.endpoints import universal_inventory, universal_warehousing, universal_ledger, universal_tracking, universal_reports, universal_intelligence

api_router.include_router(
    universal_inventory.router,
    prefix="/universal-inventory",
    tags=["Universal Inventory (Phase 1)"],
)

api_router.include_router(
    universal_warehousing.router,
    prefix="/universal-warehousing",
    tags=["Universal Warehousing & Stock Engine (Phase 2)"],
)

api_router.include_router(
    universal_ledger.router,
    prefix="/universal-ledger",
    tags=["Universal Ledger (Phase 3)"],
)

api_router.include_router(
    universal_tracking.router,
    prefix="/universal-tracking",
    tags=["Universal Batch & Serial Tracking (Phase 4)"],
)

api_router.include_router(
    universal_reports.router,
    prefix="/universal-reports",
    tags=["Universal Analytics & Reports (Phase 5)"],
)

api_router.include_router(
    universal_intelligence.router,
    prefix="/universal-intelligence",
    tags=["Universal AI Intelligence (Phase 6)"],
)

# Future module routers (uncomment as created):
from app.api.v1.endpoints import billing, auth, tenants, users, organization, rbac, audit, sessions, intelligence
# from app.api.v1.endpoints import reports
api_router.include_router(auth.router,     prefix="/auth",     tags=["Auth"])
api_router.include_router(tenants.router,  prefix="/tenants",  tags=["Tenants"])
api_router.include_router(users.router,    prefix="/users",    tags=["Users"])
api_router.include_router(organization.router, prefix="/organization", tags=["Organization"])
api_router.include_router(rbac.router,     prefix="/rbac",     tags=["RBAC"])
api_router.include_router(audit.router,    prefix="/audit",    tags=["Audit"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["Intelligence"])
# api_router.include_router(reports.router,  prefix="/reports",  tags=["Reports"])

# ---------------------------------------------------------------------------
# Phase 8 — Module 3 Omnichannel Billing & Invoice Engine
# ---------------------------------------------------------------------------
api_router.include_router(
    billing.router,
    prefix="/billing",
    tags=["Billing"],
)

# ---------------------------------------------------------------------------
# Phase 8 — Module 4 AI Copilot Ledger & Finance Engine
# ---------------------------------------------------------------------------
from app.api.v1.endpoints import finance
from app.api.v1.endpoints import finance_core
from app.api.v1.endpoints import finance_phase2
from app.api.v1.endpoints import finance_reports
from app.api.v1.endpoints import finance_phase4
from app.api.v1.endpoints import finance_phase5

api_router.include_router(
    finance.router,
    prefix="/finance",
    tags=["Finance"],
)

api_router.include_router(
    finance_core.router,
    prefix="/finance-core",
    tags=["Finance Core (Phase 1)"],
)

api_router.include_router(
    finance_phase2.router,
    prefix="/finance-phase2",
    tags=["Finance Modules (Phase 2)"],
)

api_router.include_router(
    finance_reports.router,
    prefix="/finance-reports",
    tags=["Finance Reports (Phase 3)"],
)

api_router.include_router(
    finance_phase4.router,
    prefix="/finance-phase4",
    tags=["Finance Modules (Phase 4)"],
)

api_router.include_router(
    finance_phase5.router,
    prefix="/finance-ai",
    tags=["Finance AI Copilot (Phase 5)"],
)

# ---------------------------------------------------------------------------
# Phase 8 — Module 5 Enterprise Data Migration Hub
# ---------------------------------------------------------------------------
from app.api.v1.endpoints import migration_hub, erp_connectors

api_router.include_router(
    migration_hub.router,
    prefix="/migration",
    tags=["Migration"],
)

api_router.include_router(
    erp_connectors.router,
    prefix="/migration/connectors",
    tags=["ERP Connectors"],
)

from app.api.v1.endpoints import migration_execution
api_router.include_router(
    migration_execution.router,
    prefix="/migration/execution",
    tags=["Migration Execution Engine"],
)

from app.api.v1.endpoints import migration_ai_copilot
api_router.include_router(
    migration_ai_copilot.router,
    prefix="/migration/ai-copilot",
    tags=["Migration AI Copilot"],
)

# ---------------------------------------------------------------------------
# Omnichannel Billing & Invoice Platform (Phase 1)
# ---------------------------------------------------------------------------
from app.api.v1.endpoints import universal_customers, universal_sales, universal_numbering

api_router.include_router(
    universal_customers.router,
    prefix="/omnichannel-billing/customers",
    tags=["Omnichannel Billing (Customers)"],
)

api_router.include_router(
    universal_sales.router,
    prefix="/omnichannel-billing/sales",
    tags=["Omnichannel Billing (Sales)"],
)

api_router.include_router(
    universal_numbering.router,
    prefix="/omnichannel-billing/numbering",
    tags=["Omnichannel Billing (Numbering)"],
)

# Phase 2
from app.api.v1.endpoints import universal_taxes, universal_invoices, universal_documents, universal_returns

api_router.include_router(
    universal_taxes.router,
    prefix="/omnichannel-billing/taxes",
    tags=["Omnichannel Billing (Taxes)"],
)

api_router.include_router(
    universal_invoices.router,
    prefix="/omnichannel-billing/invoices",
    tags=["Omnichannel Billing (Invoices)"],
)

api_router.include_router(
    universal_documents.router,
    prefix="/omnichannel-billing/documents",
    tags=["Omnichannel Billing (Documents)"],
)

api_router.include_router(
    universal_returns.router,
    prefix="/omnichannel-billing/returns",
    tags=["Omnichannel Billing (Returns)"],
)

# Phase 3
from app.api.v1.endpoints import universal_banks, universal_payments, universal_collections

api_router.include_router(
    universal_banks.router,
    prefix="/omnichannel-billing/banks",
    tags=["Omnichannel Billing (Banks)"],
)

api_router.include_router(
    universal_payments.router,
    prefix="/omnichannel-billing/payments",
    tags=["Omnichannel Billing (Payments)"],
)

api_router.include_router(
    universal_collections.router,
    prefix="/omnichannel-billing/collections",
    tags=["Omnichannel Billing (Collections)"],
)

# Phase 4
from app.api.v1.endpoints import universal_pos, universal_omnichannel, universal_shipping

api_router.include_router(
    universal_pos.router,
    prefix="/omnichannel-billing/pos",
    tags=["Omnichannel Billing (POS)"],
)

api_router.include_router(
    universal_omnichannel.router,
    prefix="/omnichannel-billing/channels",
    tags=["Omnichannel Billing (Channels)"],
)

api_router.include_router(
    universal_shipping.router,
    prefix="/omnichannel-billing/shipping",
    tags=["Omnichannel Billing (Shipping)"],
)

# Phase 5
from app.api.v1.endpoints import universal_analytics

api_router.include_router(
    universal_analytics.router,
    prefix="/omnichannel-billing/analytics",
    tags=["Omnichannel Billing (Analytics)"],
)

# Phase 6
from app.api.v1.endpoints import universal_ai_billing

api_router.include_router(
    universal_ai_billing.router,
    prefix="/omnichannel-billing/ai",
    tags=["Omnichannel Billing (AI Copilot)"],
)

# ---------------------------------------------------------------------------
# AI Copilot Ledger & Finance Module
# ---------------------------------------------------------------------------
from app.api.v1.endpoints import (
    finance_core,
    finance_phase2,
    finance_reports,
    finance_phase4,
    finance_phase5
)

api_router.include_router(
    finance_core.router,
    prefix="/finance-core",
    tags=["Finance Core (Phase 1)"],
)

api_router.include_router(
    finance_phase2.router,
    prefix="/finance-ar-ap",
    tags=["Finance AR/AP & Bank (Phase 2)"],
)

api_router.include_router(
    finance_reports.router,
    prefix="/finance-reports",
    tags=["Finance Reports (Phase 3)"],
)

api_router.include_router(
    finance_phase4.router,
    prefix="/finance-assets",
    tags=["Finance Assets & Budgets (Phase 4)"],
)

api_router.include_router(
    finance_phase5.router,
    prefix="/finance-ai",
    tags=["Finance AI Copilot (Phase 5)"],
)
