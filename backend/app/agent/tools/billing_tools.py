"""
app/agent/tools/billing_tools.py
==================================
First tool registry for the AI OS layer (audit #3): 3 LLM-callable tools
over the existing Billing module (app/crud/universal_invoices.py,
universal_payments.py, universal_customers.py). See app/agent/tools/__init__.py
for the package-level contract.

CRITICAL: tenant_id and user_id are never part of any tool's input_schema
--------------------------------------------------------------------------
Every handler below takes tenant_id (and, where relevant, user_id) as a
real Python parameter — but neither is ever listed in that tool's
input_schema. They must be injected by the calling code from the
authenticated request/session context, never supplied by the model. See
the package docstring for why this is a hard rule, not a preference.

Unit-of-work
------------
These handlers run outside any HTTP request, so there is no ambient
request-scoped session to share. Each opens its own db_session()
(app/core/database.py) — the same context manager get_db() wraps every
real request in — which commits once on clean exit and rolls back on any
exception. This matches the pattern already used in
app/services/agent_adapters/finance_tools.py and inventory_tools.py, and
depends on the underlying CRUD functions never calling db.commit()
themselves (Sprint 5 #1's unit-of-work refactor already guarantees this
for every function these handlers call).

@agent_tool (app/services/agent_adapters/base.py) is reused here
deliberately rather than reimplemented — one consistent enforcement point
for "no AsyncSession in an agent-facing signature" across the whole
codebase, not two parallel ones.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.core.database import db_session
from app.crud import universal_customers as crud_customers
from app.crud import universal_invoices as crud_invoices
from app.crud import universal_payments as crud_payments
from app.schemas.universal_customers import UniversalCustomerResponse
from app.schemas.universal_invoices import (
    UniversalTaxInvoiceCreate,
    UniversalTaxInvoiceItemCreate,
    UniversalTaxInvoiceResponse,
)
from app.schemas.universal_payments import (
    UniversalPaymentReceiptCreate,
    UniversalPaymentReceiptResponse,
)
from app.services.agent_adapters.base import agent_tool


@dataclass(frozen=True)
class ToolDefinition:
    """One registry entry: everything a future orchestrator needs to
    describe this tool to an LLM, enforce authorization before calling
    it, and dispatch the call. required_permission is (module, feature,
    action) — the same three strings already passed to RequirePermission
    in the corresponding HTTP endpoint; the orchestrator is responsible
    for checking it (not enforced by the handler itself — these handlers
    have no request/RBAC context to check against)."""
    name: str
    description: str
    input_schema: dict[str, Any]
    required_permission: tuple[str, str, str]
    handler: Callable[..., Awaitable[dict[str, Any]]]


# ---------------------------------------------------------------------------
# create_invoice
# ---------------------------------------------------------------------------
#
# DELIBERATE V1 RESTRICTION — not an oversight, do not "fix" by adding
# these fields back without reading this first:
#
# All seven tax-amount fields (cgst_amount/sgst_amount/igst_amount per
# line item; total_cgst/total_sgst/total_igst/tds_amount on the invoice)
# are excluded from this tool's input_schema. crud.universal_invoices.
# create_tax_invoice persists whatever tax figures it's given with zero
# calculation or validation -- there is no GST-rate lookup anywhere in
# this codebase, not even for direct API/UI callers (see
# docs/production-hardening.md, "GST/tax calculation is absent
# system-wide" for the full finding). Handing an LLM the ability to
# invent tax figures on top of that would make agent-created invoices
# less trustworthy than the already-untrusted human-entered ones.
#
# This tool can therefore only create non-tax / zero-tax invoices until
# real tax calculation exists in the underlying system -- that's tracked
# as its own, higher-priority, non-agent-specific backlog item in
# docs/production-hardening.md, not something to solve here.

_CREATE_INVOICE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_id": {"type": "string", "format": "uuid"},
        "invoice_number": {"type": "string", "maxLength": 64},
        "currency": {"type": "string", "maxLength": 3, "default": "INR"},
        "is_tax_inclusive": {"type": "boolean", "default": False},
        "items": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string", "format": "uuid"},
                    "quantity": {"type": "number", "exclusiveMinimum": 0},
                    "unit_price": {"type": "number", "minimum": 0},
                    "line_total": {"type": "number", "minimum": 0},
                    "hsn_sac_code": {"type": "string", "maxLength": 32},
                },
                "required": ["item_id", "quantity", "unit_price", "line_total"],
            },
        },
        "subtotal": {"type": "number", "minimum": 0, "default": 0},
        "total_amount": {"type": "number", "minimum": 0, "default": 0},
    },
    "required": ["customer_id", "invoice_number", "items"],
}


@agent_tool
async def handle_create_invoice(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    customer_id: uuid.UUID,
    invoice_number: str,
    items: list[dict[str, Any]],
    currency: str = "INR",
    is_tax_inclusive: bool = False,
    subtotal: float = 0.0,
    total_amount: float = 0.0,
) -> dict[str, Any]:
    # TODO(orchestrator, money-mutating): no idempotency-key protection.
    # A retried tool call after an ambiguous failure can double-create an
    # invoice. The HTTP endpoint for this same CRUD call
    # (app/api/v1/endpoints/universal_invoices.py::create_tax_invoice)
    # wraps it in claim_idempotency_key/complete_idempotency_key
    # (app/services/idempotency.py); this handler does not, because
    # generating a stable key is the orchestrator's job (it has the
    # conversation/turn context to derive one from), and no orchestrator
    # exists yet. MUST be added before this handler is wired to a live
    # agent loop -- see docs/production-hardening.md, "Agent billing
    # tools — no idempotency protection yet (money-mutating)".
    #
    # user_id is accepted (and required) for future audit-trail
    # attribution even though crud.create_tax_invoice does not currently
    # take or store it -- neither does its HTTP endpoint counterpart.
    # Not wiring AuditLogger here: it's Request-bound
    # (app/services/audit.py) and there's no HTTP request in this call
    # path; adding audit logging for non-HTTP callers is a separate,
    # deliberately out-of-scope piece of work.
    del user_id

    async with db_session() as db:
        payload = UniversalTaxInvoiceCreate(
            customer_id=customer_id,
            invoice_number=invoice_number,
            currency=currency,
            is_tax_inclusive=is_tax_inclusive,
            subtotal=subtotal,
            total_amount=total_amount,
            items=[UniversalTaxInvoiceItemCreate(**item) for item in items],
        )
        obj = await crud_invoices.create_tax_invoice(db, tenant_id, payload)
        return UniversalTaxInvoiceResponse.model_validate(obj).model_dump(mode="json")


# ---------------------------------------------------------------------------
# record_payment
# ---------------------------------------------------------------------------

_RECORD_PAYMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_id": {"type": "string", "format": "uuid"},
        "receipt_number": {"type": "string", "maxLength": 64},
        "payment_mode": {
            "type": "string",
            "maxLength": 32,
            "description": "e.g. CASH, BANK, UPI, CREDIT_CARD, DEBIT_CARD, CHEQUE, ONLINE",
        },
        "amount_received": {"type": "number", "exclusiveMinimum": 0},
        "unallocated_amount": {
            "type": "number",
            "minimum": 0,
            "description": "Portion of amount_received not yet applied to a specific invoice. Must be stated explicitly, not assumed equal to amount_received.",
        },
        "bank_account_id": {"type": "string", "format": "uuid"},
        "reference_number": {"type": "string", "maxLength": 128},
    },
    "required": ["customer_id", "receipt_number", "payment_mode", "amount_received", "unallocated_amount"],
}


@agent_tool
async def handle_record_payment(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    customer_id: uuid.UUID,
    receipt_number: str,
    payment_mode: str,
    amount_received: float,
    unallocated_amount: float,
    bank_account_id: uuid.UUID | None = None,
    reference_number: str | None = None,
) -> dict[str, Any]:
    # TODO(orchestrator, money-mutating): same idempotency gap as
    # handle_create_invoice above -- see that function's TODO and
    # docs/production-hardening.md for the full explanation. A retried
    # call here can double-record a payment and double-credit a
    # customer's wallet (crud.create_payment_receipt credits
    # UniversalCustomerWallet when unallocated_amount > 0). MUST be
    # fixed before this handler is wired to a live agent loop.
    #
    # user_id: same future-audit-attribution note as
    # handle_create_invoice -- not currently stored or used.
    del user_id

    async with db_session() as db:
        payload = UniversalPaymentReceiptCreate(
            customer_id=customer_id,
            bank_account_id=bank_account_id,
            receipt_number=receipt_number,
            payment_mode=payment_mode,
            reference_number=reference_number,
            amount_received=amount_received,
            unallocated_amount=unallocated_amount,
        )
        obj = await crud_payments.create_payment_receipt(db, tenant_id, payload)
        return UniversalPaymentReceiptResponse.model_validate(obj).model_dump(mode="json")


# ---------------------------------------------------------------------------
# search_customer
# ---------------------------------------------------------------------------

_SEARCH_CUSTOMER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "search": {"type": "string", "description": "Partial or full customer name to search for"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
    },
    "required": ["search"],
}


@agent_tool
async def handle_search_customer(
    tenant_id: uuid.UUID,
    search: str,
    limit: int = 20,
) -> dict[str, Any]:
    # Read-only: no user_id, no idempotency concern.
    async with db_session() as db:
        items, total = await crud_customers.list_customers(db, tenant_id, limit=limit, offset=0, search=search)
        return {
            "items": [UniversalCustomerResponse.model_validate(obj).model_dump(mode="json") for obj in items],
            "total": total,
        }


BILLING_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="create_invoice",
        description=(
            "Create a tax invoice for a customer with one or more line items. "
            "v1 restriction: only non-tax / zero-tax invoices are supported -- "
            "this tool has no tax-amount fields because the underlying system "
            "does not calculate GST. Amounts must be provided explicitly, not "
            "computed by the model."
        ),
        input_schema=_CREATE_INVOICE_SCHEMA,
        required_permission=("UniversalBilling", "Invoices", "Create"),
        handler=handle_create_invoice,
    ),
    ToolDefinition(
        name="record_payment",
        description=(
            "Record a payment received from a customer against their account, "
            "optionally leaving part of it unallocated for later application "
            "to specific invoices."
        ),
        input_schema=_RECORD_PAYMENT_SCHEMA,
        required_permission=("UniversalBilling", "Payments", "Create"),
        handler=handle_record_payment,
    ),
    ToolDefinition(
        name="search_customer",
        description=(
            "Search for existing customers by name (partial match). Use this "
            "to find a customer_id before creating an invoice or recording a payment."
        ),
        input_schema=_SEARCH_CUSTOMER_SCHEMA,
        required_permission=("UniversalBilling", "Customers", "Read"),
        handler=handle_search_customer,
    ),
]
