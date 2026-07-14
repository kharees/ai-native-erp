"""
tests/test_universal_intelligence.py
======================================
Verifies app/services/universal_intelligence.py's real-data-in,
AI-for-judgment-only design (Sprint 5 AI foundation follow-up): every
quantity/dollar-value/date in a response comes from real seeded rows in
the test database; the AI provider is mocked (no live API key available
in this environment — same convention as tests/test_ai_provider.py) and
is only asked to supply the qualitative fields (health_score, rationale,
recommendation_type, seasonality_trend, response_text) — never the
numbers, which the test independently computes from the same seeded data
and asserts against directly.

get_ai_provider is patched at app.services.universal_intelligence's own
import of it (not app.services.ai.factory), matching how Python binds
`from x import y` — patching factory.get_ai_provider would not affect the
name already bound inside universal_intelligence's module namespace.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.universal_inventory import UniversalItemMaster
from app.models.universal_ledger import UniversalInventoryLedger
from app.models.universal_tracking import UniversalBatchMaster, UniversalBatchStock
from app.models.universal_warehousing import UniversalStockBalance, UniversalWarehouse
from app.services.ai.base import AIProviderNotConfiguredError

pytestmark = pytest.mark.asyncio


async def _seed_inventory_scenario(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """
    Seeds real rows for four distinct, independently-verifiable scenarios:
      - a dead-stock item (on-hand stock, no movement in 200 days)
      - a fast-moving item (recent outbound ledger movement -> forecast candidate)
      - an item with a batch expiring in 10 days
      - an out-of-stock item (available quantity <= 0)
    Returns the raw numbers the test needs to compute expected values
    independently of the service under test.
    """
    now = datetime.now(timezone.utc)
    warehouse = UniversalWarehouse(tenant_id=tenant_id, code="WH-AI", name="AI Test Warehouse")
    db.add(warehouse)
    await db.flush()

    # --- Dead stock item: 50 units, last touched 200 days ago, real unit_cost via ledger ---
    dead_item = UniversalItemMaster(
        tenant_id=tenant_id, item_code="AI-DEAD-1", sku="AI-DEAD-1", name="Stale Widget",
    )
    db.add(dead_item)
    await db.flush()
    dead_balance = UniversalStockBalance(
        tenant_id=tenant_id, item_id=dead_item.id, warehouse_id=warehouse.id,
        quantity_on_hand=Decimal("50"), last_transaction_at=now - timedelta(days=200),
    )
    db.add(dead_balance)
    dead_ledger = UniversalInventoryLedger(
        tenant_id=tenant_id, item_id=dead_item.id, warehouse_id=warehouse.id,
        quantity_before=Decimal("0"), movement_quantity=Decimal("50"), quantity_after=Decimal("50"),
        unit_cost=Decimal("10.00"), total_cost=Decimal("500.00"), reference_type="seed",
        created_at=now - timedelta(days=200),
    )
    db.add(dead_ledger)

    # --- Fast-moving item: recent outbound ledger movement -> forecast candidate ---
    moving_item = UniversalItemMaster(
        tenant_id=tenant_id, item_code="AI-MOVE-1", sku="AI-MOVE-1", name="Popular Gadget",
    )
    db.add(moving_item)
    await db.flush()
    moving_balance = UniversalStockBalance(
        tenant_id=tenant_id, item_id=moving_item.id, warehouse_id=warehouse.id,
        quantity_on_hand=Decimal("300"), last_transaction_at=now - timedelta(days=1),
    )
    db.add(moving_balance)
    # 3 outbound movements of 30 units each within the trailing 90-day window
    total_out = Decimal("0")
    for i in range(3):
        db.add(UniversalInventoryLedger(
            tenant_id=tenant_id, item_id=moving_item.id, warehouse_id=warehouse.id,
            quantity_before=Decimal("300"), movement_quantity=Decimal("-30"), quantity_after=Decimal("270"),
            unit_cost=Decimal("5.00"), total_cost=Decimal("150.00"), reference_type="seed",
            created_at=now - timedelta(days=10 * (i + 1)),
        ))
        total_out += Decimal("30")

    # --- Expiring batch item: batch expiring in 10 days, 20 units on hand ---
    expiring_item = UniversalItemMaster(
        tenant_id=tenant_id, item_code="AI-EXP-1", sku="AI-EXP-1", name="Seasonal Snack",
    )
    db.add(expiring_item)
    await db.flush()
    batch = UniversalBatchMaster(
        tenant_id=tenant_id, item_id=expiring_item.id, batch_number="BATCH-AI-001",
        expiry_date=date.today() + timedelta(days=10),
    )
    db.add(batch)
    await db.flush()
    db.add(UniversalBatchStock(
        tenant_id=tenant_id, batch_id=batch.id, warehouse_id=warehouse.id, quantity_on_hand=Decimal("20"),
    ))

    # --- Out-of-stock item: available (on_hand - reserved - allocated) == 0 ---
    oos_item = UniversalItemMaster(
        tenant_id=tenant_id, item_code="AI-OOS-1", sku="AI-OOS-1", name="Sold Out Item",
    )
    db.add(oos_item)
    await db.flush()
    db.add(UniversalStockBalance(
        tenant_id=tenant_id, item_id=oos_item.id, warehouse_id=warehouse.id,
        quantity_on_hand=Decimal("0"), quantity_reserved=Decimal("0"), quantity_allocated=Decimal("0"),
        last_transaction_at=now,
    ))

    await db.commit()

    return {
        "dead_item_id": dead_item.id,
        "dead_tied_up_value": 500.0,  # 50 * 10.00
        "moving_item_id": moving_item.id,
        "moving_current_stock": 300.0,
        "moving_projected_demand_30d": round((float(total_out) / 90.0) * 30, 2),
        "batch_number": "BATCH-AI-001",
        "expiring_item_name": "Seasonal Snack",
        "oos_item_name": "Sold Out Item",
    }


def _mock_provider(complete_return_value=None, complete_side_effect=None):
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=complete_return_value, side_effect=complete_side_effect)
    return provider


async def test_ai_dashboard_grounds_numbers_in_real_data_and_uses_ai_only_for_judgment(
    async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession, setup_tenant
):
    seeded = await _seed_inventory_scenario(db_session, setup_tenant.id)

    ai_json_response = (
        '{"health_score": 52.5, '
        '"dead_stock_recommendations": [{"item_id": "%s", "recommendation_type": "Liquidate", '
        '"rationale": "Sitting idle for 200 days with no forecasted demand."}], '
        '"forecast_trends": [{"item_id": "%s", "seasonality_trend": "Increasing"}]}'
    ) % (seeded["dead_item_id"], seeded["moving_item_id"])

    mock_provider = _mock_provider(complete_return_value=ai_json_response)
    with patch("app.services.universal_intelligence.get_ai_provider", return_value=mock_provider):
        res = await async_client.get("/api/v1/universal-intelligence/dashboard", headers=auth_headers)

    assert res.status_code == 200, res.text
    data = res.json()

    # health_score came from the AI mock, not a hardcoded value in the code
    assert data["health_score"] == 52.5

    # Recommendation's dollar figure and current level are real, computed
    # from seeded ledger/stock rows -- not something the AI mock supplied.
    dead_rec = next(r for r in data["recommendations"] if r["item_id"] == str(seeded["dead_item_id"]))
    assert dead_rec["potential_savings"] == seeded["dead_tied_up_value"]
    assert dead_rec["current_level"] == 50.0
    # Rationale IS AI-supplied -- this is the qualitative field the mock controls.
    assert dead_rec["rationale"] == "Sitting idle for 200 days with no forecasted demand."
    assert dead_rec["recommendation_type"] == "Liquidate"

    # Forecast's demand projection is real arithmetic over seeded ledger
    # rows (trailing-90-day average * 30), independently recomputed here.
    forecast = next(f for f in data["forecasts"] if f["item_id"] == str(seeded["moving_item_id"]))
    assert forecast["current_stock"] == seeded["moving_current_stock"]
    assert forecast["projected_demand_30d"] == seeded["moving_projected_demand_30d"]
    assert forecast["seasonality_trend"] == "Increasing"  # AI-supplied classification

    # Alerts reflect real seeded batch/stock rows, not fabricated examples.
    messages = [a["message"] for a in data["alerts"]]
    assert any(seeded["batch_number"] in m and "10 days" in m for m in messages)
    assert any(seeded["oos_item_name"] in m for m in messages)

    # The AI was actually called, and given the real numbers -- not a
    # generic/empty prompt. Spot-check a real fact made it into the call.
    mock_provider.complete.assert_called_once()
    call_kwargs = mock_provider.complete.call_args
    prompt_text = str(call_kwargs)
    assert "500.0" in prompt_text or "500" in prompt_text
    assert "Stale Widget" in prompt_text


async def test_ai_dashboard_raises_instead_of_fabricating_when_ai_unconfigured(
    async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession, setup_tenant
):
    """AIProviderNotConfiguredError must propagate rather than being
    swallowed with a fabricated dashboard -- the explicit contract in
    app/services/ai/base.py and this module's own docstring.

    Asserting a raised exception here, not a 500 response: this app's
    request_logging_middleware (@app.middleware("http"), which Starlette
    implements as BaseHTTPMiddleware -- see main.py) has the same
    exception-propagation limitation already documented in
    docs/production-hardening.md for TenantAuthMiddleware. main.py's
    global exception handler does run (confirmed via its log line) but
    the resulting response can't pass back through that middleware, so it
    surfaces to the test client as a raised exception instead of a clean
    500 JSON body. That's a pre-existing architectural gap, not something
    this change introduced or is in scope to fix -- the property this
    test actually needs to prove (the error is never swallowed in favor
    of fabricated data) holds either way.
    """
    await _seed_inventory_scenario(db_session, setup_tenant.id)

    with patch(
        "app.services.universal_intelligence.get_ai_provider",
        side_effect=AIProviderNotConfiguredError("no key configured"),
    ):
        with pytest.raises(AIProviderNotConfiguredError):
            await async_client.get("/api/v1/universal-intelligence/dashboard", headers=auth_headers)


async def test_ai_copilot(async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession, setup_tenant):
    await _seed_inventory_scenario(db_session, setup_tenant.id)

    # 1. Low stock intent -- AI phrases the real seeded count (1 out-of-stock item).
    mock_provider = _mock_provider(complete_return_value="1 item is currently at or below available stock.")
    with patch("app.services.universal_intelligence.get_ai_provider", return_value=mock_provider):
        res1 = await async_client.post(
            "/api/v1/universal-intelligence/copilot/ask",
            json={"query": "Show me the low stock items"},
            headers=auth_headers,
        )
    assert res1.status_code == 200
    assert res1.json()["intent"] == "FIND_LOW_STOCK"
    assert res1.json()["response_text"] == "1 item is currently at or below available stock."
    mock_provider.complete.assert_called_once()
    assert "1" in str(mock_provider.complete.call_args)

    # 2. Expiry intent -- AI phrases the real seeded expiring-batch count (1).
    mock_provider2 = _mock_provider(complete_return_value="1 batch is expiring within the next 30 days.")
    with patch("app.services.universal_intelligence.get_ai_provider", return_value=mock_provider2):
        res2 = await async_client.post(
            "/api/v1/universal-intelligence/copilot/ask",
            json={"query": "What is going to expire next month?"},
            headers=auth_headers,
        )
    assert res2.status_code == 200
    assert res2.json()["intent"] == "FIND_EXPIRY"
    assert res2.json()["response_text"] == "1 batch is expiring within the next 30 days."

    # 3. General/unknown intent -- static help text, no AI call made at all.
    mock_provider3 = _mock_provider()
    with patch("app.services.universal_intelligence.get_ai_provider", return_value=mock_provider3) as get_provider:
        res3 = await async_client.post(
            "/api/v1/universal-intelligence/copilot/ask",
            json={"query": "How are you today?"},
            headers=auth_headers,
        )
    assert res3.status_code == 200
    assert res3.json()["intent"] == "GENERAL_INVENTORY_ASSIST"
    get_provider.assert_not_called()
