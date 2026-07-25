"""
tests/test_orchestrator.py
=============================
Exercises app/agent/orchestrator/loop.py end-to-end: real database, real
Billing tool handlers, real RBAC checks -- only the AI provider is a test
double (a scripted sequence of AIToolCallResult objects), same boundary
tests/test_billing_tools.py and tests/test_ai_provider.py already draw
the line at (no live API key in this environment).

Covers, each mapped to a design decision confirmed before this was built:
  - a non-gated tool (search_customer) dispatches immediately, no pause
  - a requires_confirmation tool (create_invoice) pauses with the exact
    proposed call, nothing dispatched yet
  - resuming confirmed=True dispatches that exact call (same id -> same
    idempotency_key), creating a real row
  - resuming confirmed=False dispatches nothing, feeds back a decline
  - a denied RBAC check never reaches the handler (no DB write)
  - an unknown tool name is handled gracefully, not a crash
  - a real 409 (stuck idempotency claim) is classified as STUCK_CONFLICT
    and a second request for the same tool in the same batch is refused
    locally, without a second dispatch attempt
  - the iteration cap actually stops an otherwise-infinite tool-call loop
"""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.agent.orchestrator import run_turn, resume_after_confirmation
from app.agent.tools.base import ToolDefinition
from app.agent.tools.billing_tools import BILLING_TOOLS
from app.core.database import db_session
from app.middleware.rbac import _clear_permission_cache
from app.crud import universal_warehousing as crud_warehousing
from app.models.rbac import TenantPermission, TenantRole, TenantRolePermission, TenantUserRole
from app.models.tenants import Tenant
from app.models.auth import UserAccount
from app.models.users import UserProfile
from app.models.universal_customers import UniversalCustomer
from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_invoices import UniversalTaxInvoice
from app.models.universal_ledger import UniversalInventoryLedger
from app.models.universal_warehousing import UniversalStockBalance, UniversalStockTransaction, UniversalWarehouse
from app.models.idempotency import IdempotencyKey
from app.schemas.universal_warehousing import StockMovementRequest
from app.services.ai.base import AIToolCall, AIToolCallResult

pytestmark = pytest.mark.asyncio

_ALL_BILLING_PERMISSIONS = [
    ("UniversalBilling", "Invoices", "Create"),
    ("UniversalBilling", "Payments", "Create"),
    ("UniversalBilling", "Customers", "Read"),
]


class _ScriptedProvider:
    """Test double for AIProvider: complete_with_tools() returns each
    entry of `script` in order, one per call. Records every call's
    (messages, tools) for inspection."""

    def __init__(self, script: list[AIToolCallResult]):
        self._script = list(script)
        self.calls: list[tuple] = []

    async def complete_with_tools(self, messages, tools, *, system=None, max_tokens=1024, temperature=0.7):
        self.calls.append((messages, tools))
        return self._script.pop(0)


async def _make_tenant_and_user(permissions: list[tuple[str, str, str]]) -> tuple[uuid.UUID, uuid.UUID]:
    _clear_permission_cache()
    now = datetime.now(timezone.utc)
    async with db_session() as db:
        tenant = Tenant(name="Orchestrator Test", slug=f"orch-{uuid.uuid4().hex[:10]}", plan="enterprise")
        db.add(tenant)
        await db.flush()

        user_id = uuid.uuid4()
        db.add(UserAccount(id=user_id, email=f"{user_id}@example.com", hashed_password="x", is_active=True))
        await db.flush()

        profile = UserProfile(user_id=user_id, tenant_id=tenant.id, first_name="Orchestrator Test User", is_active=True)
        db.add(profile)
        await db.flush()

        if permissions:
            role = TenantRole(tenant_id=tenant.id, name="Orchestrator Test Role", is_system=False, hierarchy_level=100)
            db.add(role)
            await db.flush()
            for module, feature, action in permissions:
                # TenantPermission is a global catalog table (no tenant_id,
                # unique on (module, feature, action)) -- get-or-create
                # rather than blind-insert, since a full-suite run has many
                # tests requesting the same tuple and this file's own
                # cleanup never deletes catalog rows (correctly -- other
                # tests running concurrently/afterward may still need them).
                perm = (await db.execute(
                    select(TenantPermission).where(
                        TenantPermission.module == module,
                        TenantPermission.feature == feature,
                        TenantPermission.action == action,
                    )
                )).scalar_one_or_none()
                if perm is None:
                    perm = TenantPermission(module=module, feature=feature, action=action)
                    db.add(perm)
                    await db.flush()
                db.add(TenantRolePermission(role_id=role.id, permission_id=perm.id, conditions={}))
                await db.flush()
            db.add(TenantUserRole(tenant_id=tenant.id, user_id=profile.id, role_id=role.id))

        return tenant.id, user_id


async def _make_customer(tenant_id: uuid.UUID, name: str = "Acme Corp") -> uuid.UUID:
    async with db_session() as db:
        customer = UniversalCustomer(tenant_id=tenant_id, name=name, email=f"{uuid.uuid4().hex[:8]}@example.com")
        db.add(customer)
        await db.flush()
        await db.refresh(customer)
        return customer.id


async def _make_item(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        item = UniversalItemMaster(
            tenant_id=tenant_id, item_code=f"ORCH-{uuid.uuid4().hex[:8]}",
            sku=f"ORCH-SKU-{uuid.uuid4().hex[:8]}", name="Orchestrator Test Item",
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item.id


async def _make_warehouse(tenant_id: uuid.UUID) -> uuid.UUID:
    async with db_session() as db:
        warehouse = UniversalWarehouse(tenant_id=tenant_id, name="Orchestrator Test WH", code=f"ORCH-WH-{uuid.uuid4().hex[:8]}")
        db.add(warehouse)
        await db.flush()
        await db.refresh(warehouse)
        return warehouse.id


async def _seed_stock(tenant_id: uuid.UUID, item_id: uuid.UUID, warehouse_id: uuid.UUID, quantity: float) -> None:
    async with db_session() as db:
        await crud_warehousing.execute_stock_movement(
            db, tenant_id, None,
            StockMovementRequest(
                item_id=item_id, warehouse_id=warehouse_id, transaction_type="IN",
                reference_type="test_seed", quantity=quantity,
            ),
        )


async def _cleanup(*tenant_ids: uuid.UUID) -> None:
    async with db_session() as db:
        for tenant_id in tenant_ids:
            await db.execute(delete(IdempotencyKey).where(IdempotencyKey.tenant_id == tenant_id))
            await db.execute(delete(UniversalInventoryLedger).where(UniversalInventoryLedger.tenant_id == tenant_id))
            await db.execute(delete(UniversalStockTransaction).where(UniversalStockTransaction.tenant_id == tenant_id))
            await db.execute(delete(UniversalStockBalance).where(UniversalStockBalance.tenant_id == tenant_id))
            await db.execute(delete(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id))
            await db.execute(delete(UniversalItemMaster).where(UniversalItemMaster.tenant_id == tenant_id))
            await db.execute(delete(UniversalWarehouse).where(UniversalWarehouse.tenant_id == tenant_id))
            await db.execute(delete(UniversalCustomer).where(UniversalCustomer.tenant_id == tenant_id))
            await db.execute(delete(TenantUserRole).where(TenantUserRole.tenant_id == tenant_id))
            await db.execute(delete(TenantRolePermission).where(
                TenantRolePermission.role_id.in_(select(TenantRole.id).where(TenantRole.tenant_id == tenant_id))
            ))
            await db.execute(delete(TenantRole).where(TenantRole.tenant_id == tenant_id))
            await db.execute(delete(UserProfile).where(UserProfile.tenant_id == tenant_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


def _call(name: str, arguments: dict, call_id: str = "call_1") -> AIToolCall:
    return AIToolCall(id=call_id, name=name, arguments=arguments)


async def test_non_gated_tool_dispatches_immediately_and_completes():
    tenant_id, user_id = await _make_tenant_and_user(_ALL_BILLING_PERMISSIONS)
    await _make_customer(tenant_id, name="Widget Traders")
    try:
        provider = _ScriptedProvider([
            AIToolCallResult(text=None, tool_calls=[_call("search_customer", {"search": "Widget"})]),
            AIToolCallResult(text="Found Widget Traders.", tool_calls=[]),
        ])

        result = await run_turn(
            tenant_id=tenant_id, user_id=user_id, conversation_id="conv-1",
            messages=[{"role": "user", "content": "find Widget"}],
            provider=provider, tools=BILLING_TOOLS,
        )

        assert result.status == "done"
        assert result.text == "Found Widget Traders."
        # tool_result actually contains the real DB match, not a stub.
        tool_result_msg = next(m for m in result.messages if m.get("role") == "tool_result")
        assert "Widget Traders" in tool_result_msg["content"]
    finally:
        await _cleanup(tenant_id)


async def test_money_mutating_tool_pauses_for_confirmation_and_dispatches_nothing():
    tenant_id, user_id = await _make_tenant_and_user(_ALL_BILLING_PERMISSIONS)
    customer_id = await _make_customer(tenant_id)
    item_id = await _make_item(tenant_id)
    try:
        proposed_call = _call("create_invoice", {
            "customer_id": str(customer_id),
            "items": [{"item_id": str(item_id), "quantity": 1, "unit_price": 10.0, "line_total": 10.0}],
        })
        provider = _ScriptedProvider([AIToolCallResult(text=None, tool_calls=[proposed_call])])

        result = await run_turn(
            tenant_id=tenant_id, user_id=user_id, conversation_id="conv-2",
            messages=[{"role": "user", "content": "invoice Acme for 10"}],
            provider=provider, tools=BILLING_TOOLS,
        )

        assert result.status == "awaiting_confirmation"
        assert result.pending_tool_call == proposed_call

        async with db_session() as verify_db:
            invoices = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalars().all()
            assert invoices == []  # nothing dispatched yet
    finally:
        await _cleanup(tenant_id)


async def test_resume_confirmed_dispatches_exact_call_and_creates_real_row():
    tenant_id, user_id = await _make_tenant_and_user(_ALL_BILLING_PERMISSIONS)
    customer_id = await _make_customer(tenant_id)
    item_id = await _make_item(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 1)
    try:
        proposed_call = _call("create_invoice", {
            "customer_id": str(customer_id),
            "warehouse_id": str(warehouse_id),
            "items": [{"item_id": str(item_id), "quantity": 1, "unit_price": 20.0, "line_total": 20.0}],
        }, call_id="call_abc")

        pause = await run_turn(
            tenant_id=tenant_id, user_id=user_id, conversation_id="conv-3",
            messages=[{"role": "user", "content": "invoice Acme for 20"}],
            provider=_ScriptedProvider([AIToolCallResult(text=None, tool_calls=[proposed_call])]),
            tools=BILLING_TOOLS,
        )
        assert pause.status == "awaiting_confirmation"

        resume_provider = _ScriptedProvider([AIToolCallResult(text="Invoice created.", tool_calls=[])])
        result = await resume_after_confirmation(
            tenant_id=tenant_id, user_id=user_id, conversation_id="conv-3",
            messages=pause.messages, pending_tool_call=pause.pending_tool_call, confirmed=True,
            provider=resume_provider, tools=BILLING_TOOLS,
        )

        assert result.status == "done"

        async with db_session() as verify_db:
            invoice = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalar_one()
            # Server-generated (GST-compliant, gapless numbering -- see
            # app/services/gst_compliance.py), not the arbitrary literal the
            # caller no longer even has the option of supplying.
            assert invoice.invoice_number.startswith("INV/")

            # idempotency_key used was exactly f"{conversation_id}:{tool_call_id}"
            # -- the captured id, not a freshly generated one.
            claim = (await verify_db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id,
                    IdempotencyKey.endpoint == "sales.invoice_with_stock_deduction",
                )
            )).scalar_one()
            assert claim.key == "conv-3:call_abc"
            assert claim.status == "completed"
    finally:
        await _cleanup(tenant_id)


async def test_resume_declined_dispatches_nothing():
    tenant_id, user_id = await _make_tenant_and_user(_ALL_BILLING_PERMISSIONS)
    customer_id = await _make_customer(tenant_id)
    item_id = await _make_item(tenant_id)
    try:
        proposed_call = _call("create_invoice", {
            "customer_id": str(customer_id),
            "items": [{"item_id": str(item_id), "quantity": 1, "unit_price": 5.0, "line_total": 5.0}],
        })
        pause = await run_turn(
            tenant_id=tenant_id, user_id=user_id, conversation_id="conv-4",
            messages=[{"role": "user", "content": "invoice for 5"}],
            provider=_ScriptedProvider([AIToolCallResult(text=None, tool_calls=[proposed_call])]),
            tools=BILLING_TOOLS,
        )

        resume_provider = _ScriptedProvider([AIToolCallResult(text="Okay, not creating that invoice.", tool_calls=[])])
        result = await resume_after_confirmation(
            tenant_id=tenant_id, user_id=user_id, conversation_id="conv-4",
            messages=pause.messages, pending_tool_call=pause.pending_tool_call, confirmed=False,
            provider=resume_provider, tools=BILLING_TOOLS,
        )

        assert result.status == "done"
        async with db_session() as verify_db:
            invoices = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalars().all()
            assert invoices == []

        # The model's follow-up call saw a "declined" tool_result, not an error.
        declined_msg = resume_provider.calls[0][0][-1]
        assert '"declined"' in declined_msg["content"]
    finally:
        await _cleanup(tenant_id)


async def test_permission_denied_never_reaches_handler():
    # No permissions granted at all.
    tenant_id, user_id = await _make_tenant_and_user(permissions=[])
    try:
        provider = _ScriptedProvider([
            AIToolCallResult(text=None, tool_calls=[_call("search_customer", {"search": "anything"})]),
            AIToolCallResult(text="You don't have access to search customers.", tool_calls=[]),
        ])

        result = await run_turn(
            tenant_id=tenant_id, user_id=user_id, conversation_id="conv-5",
            messages=[{"role": "user", "content": "find a customer"}],
            provider=provider, tools=BILLING_TOOLS,
        )

        assert result.status == "done"
        tool_result_msg = next(m for m in result.messages if m.get("role") == "tool_result")
        assert "permission_denied" in tool_result_msg["content"]
    finally:
        await _cleanup(tenant_id)


async def test_unknown_tool_name_handled_gracefully():
    tenant_id, user_id = await _make_tenant_and_user(_ALL_BILLING_PERMISSIONS)
    try:
        provider = _ScriptedProvider([
            AIToolCallResult(text=None, tool_calls=[_call("delete_everything", {})]),
            AIToolCallResult(text="I don't have a tool for that.", tool_calls=[]),
        ])

        result = await run_turn(
            tenant_id=tenant_id, user_id=user_id, conversation_id="conv-6",
            messages=[{"role": "user", "content": "do something unsupported"}],
            provider=provider, tools=BILLING_TOOLS,
        )

        assert result.status == "done"
        tool_result_msg = next(m for m in result.messages if m.get("role") == "tool_result")
        assert "unknown_tool" in tool_result_msg["content"]
    finally:
        await _cleanup(tenant_id)


async def test_stuck_conflict_classified_via_real_idempotency_race():
    """create_invoice requires confirmation, so the only path that ever
    dispatches it is resume_after_confirmation. To reproduce a genuine 409
    from app/services/idempotency.py (not a simulated one), a real,
    freshly-created "pending" IdempotencyKey row is inserted directly
    under the exact key resume_after_confirmation will use
    (f"{conversation_id}:{tool_call_id}", see run_turn/resume_after_
    confirmation's own docstrings) -- simulating another request for the
    same tool call that is genuinely still in flight.

    Previously this test manufactured a "stuck" claim by having a first
    attempt fail validation (customer ownership) and rely on the claim
    being left behind afterward -- that was the exact bug
    app/services/idempotency.py's release_idempotency_key now fixes (a
    rejected request no longer leaves its claim behind at all), so that
    approach no longer reproduces a stuck claim. A directly-inserted,
    still-genuinely-pending row is the correct way to exercise
    STUCK_CONFLICT classification now -- see
    tests/omnichannel_billing/test_idempotency_release.py for the
    complementary "a rejected request's claim really is gone, and a
    genuinely in-flight one still 409s" regression tests.
    """
    tenant_id, user_id = await _make_tenant_and_user(_ALL_BILLING_PERMISSIONS)
    item_id = await _make_item(tenant_id)
    warehouse_id = await _make_warehouse(tenant_id)
    customer_id = await _make_customer(tenant_id)
    await _seed_stock(tenant_id, item_id, warehouse_id, 10)
    conversation_id = "conv-7"
    call_id = "call_stuck"
    try:
        proposed_call = _call("create_invoice", {
            "customer_id": str(customer_id),
            "warehouse_id": str(warehouse_id),
            "items": [{"item_id": str(item_id), "quantity": 1, "unit_price": 1.0, "line_total": 1.0}],
        }, call_id=call_id)

        pause = await run_turn(
            tenant_id=tenant_id, user_id=user_id, conversation_id=conversation_id,
            messages=[{"role": "user", "content": "invoice a customer"}],
            provider=_ScriptedProvider([AIToolCallResult(text=None, tool_calls=[proposed_call])]),
            tools=BILLING_TOOLS,
        )

        # A genuinely in-flight claim for the exact call about to be
        # resumed -- same key resume_after_confirmation will derive.
        async with db_session() as db:
            db.add(IdempotencyKey(
                tenant_id=tenant_id, endpoint="sales.invoice_with_stock_deduction",
                key=f"{conversation_id}:{call_id}", status="pending",
            ))
            await db.commit()

        resume = await resume_after_confirmation(
            tenant_id=tenant_id, user_id=user_id, conversation_id=conversation_id,
            messages=pause.messages, pending_tool_call=pause.pending_tool_call, confirmed=True,
            provider=_ScriptedProvider([AIToolCallResult(text="That could not be created; it may already be in progress.", tool_calls=[])]),
            tools=BILLING_TOOLS,
        )
        tool_result = next(
            m for m in resume.messages[len(pause.messages):] if m.get("role") == "tool_result"
        )
        assert "stuck_conflict" in tool_result["content"]
        assert "may already be in progress" in tool_result["content"]

        # Nothing was created, and the claim is untouched -- still pending.
        async with db_session() as verify_db:
            invoices = (await verify_db.execute(
                select(UniversalTaxInvoice).where(UniversalTaxInvoice.tenant_id == tenant_id)
            )).scalars().all()
            assert invoices == []
            claim_row = (await verify_db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id,
                    IdempotencyKey.endpoint == "sales.invoice_with_stock_deduction",
                    IdempotencyKey.key == f"{conversation_id}:{call_id}",
                )
            )).scalar_one()
            assert claim_row.status == "pending"
    finally:
        await _cleanup(tenant_id)


async def test_stuck_call_id_not_retried_within_same_batch():
    """Isolated test of run_turn's own local-refusal logic (call-id-scoped,
    not tool-name-scoped -- a stuck call must not block a different,
    unrelated future call to the same tool) against a synthetic
    always-409 tool that does NOT require confirmation, so both entries
    in one batch actually reach the dispatch loop instead of being
    intercepted by a confirmation pause first."""
    handler_calls = []

    async def _always_stuck_handler(tenant_id, **kwargs):
        handler_calls.append(kwargs)
        raise HTTPException(status_code=409, detail="stuck")

    stuck_tool = ToolDefinition(
        name="always_stuck",
        description="test double",
        input_schema={"type": "object", "properties": {}},
        required_permission=("UniversalBilling", "Invoices", "Create"),
        handler=_always_stuck_handler,
        requires_confirmation=False,
    )
    # Grant the permission this synthetic tool declares, same as any real one.
    tenant_id, user_id = await _make_tenant_and_user([("UniversalBilling", "Invoices", "Create")])
    try:
        same_call_twice = [
            _call("always_stuck", {}, call_id="dup_1"),
            _call("always_stuck", {}, call_id="dup_1"),
        ]
        provider = _ScriptedProvider([
            AIToolCallResult(text=None, tool_calls=same_call_twice),
            AIToolCallResult(text="That action could not be completed.", tool_calls=[]),
        ])

        result = await run_turn(
            tenant_id=tenant_id, user_id=user_id, conversation_id="conv-9",
            messages=[{"role": "user", "content": "do the stuck thing"}],
            provider=provider, tools=[stuck_tool],
        )

        assert result.status == "done"
        assert len(handler_calls) == 1  # not 2 -- the repeated same-batch call_id was refused locally
        stuck_messages = [m for m in result.messages if m.get("role") == "tool_result" and "stuck_conflict" in m["content"]]
        assert len(stuck_messages) == 2  # the real 409 AND the locally-refused repeat both surface as stuck_conflict
    finally:
        await _cleanup(tenant_id)


async def test_max_iterations_cap_stops_an_otherwise_infinite_loop():
    tenant_id, user_id = await _make_tenant_and_user(_ALL_BILLING_PERMISSIONS)
    try:
        # A provider that always wants to call search_customer again,
        # forever -- proves the cap actually bounds the loop rather than
        # this test hanging or the loop running away.
        endless_script = [
            AIToolCallResult(text=None, tool_calls=[_call("search_customer", {"search": "x"}, call_id=f"call_{i}")])
            for i in range(10)
        ]
        provider = _ScriptedProvider(endless_script)

        result = await run_turn(
            tenant_id=tenant_id, user_id=user_id, conversation_id="conv-8",
            messages=[{"role": "user", "content": "keep searching"}],
            provider=provider, tools=BILLING_TOOLS, max_iterations=3,
        )

        assert result.status == "max_iterations_reached"
        assert result.text is None
        assert len(provider.calls) == 3
    finally:
        await _cleanup(tenant_id)
