"""
app/services/agent_adapters/
==============================
Sprint 5 (#2, audit #6): the only functions in this codebase considered
safe to register as AI tools once a tool registry/orchestrator exists
(audit #3 — not built yet, see docs/ai-foundation.md). Every function
here is decorated with @agent_tool (base.py), which structurally forbids
an AsyncSession/AsyncConnection parameter at import time.

This package does not implement tool registration, JSON-schema generation,
or an agent loop — see docs/ai-foundation.md for what's built and what
remains. It implements the narrower precondition: a curated set of
adapters over the existing app/crud layer that are actually safe to hand
to a model.
"""

from app.services.agent_adapters.base import AgentToolSignatureError, agent_tool
from app.services.agent_adapters.finance_tools import (
    create_account,
    create_and_post_journal_voucher,
    get_account,
    list_accounts,
)
from app.services.agent_adapters.inventory_tools import (
    create_item,
    execute_stock_movement,
    get_item,
)

__all__ = [
    "agent_tool",
    "AgentToolSignatureError",
    "get_account",
    "list_accounts",
    "create_account",
    "create_and_post_journal_voucher",
    "get_item",
    "create_item",
    "execute_stock_movement",
]
