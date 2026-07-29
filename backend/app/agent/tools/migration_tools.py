"""
app/agent/tools/migration_tools.py
=====================================
Migration tools for the consolidated AI orchestrator (app/agent/
orchestrator/loop.py) -- follows the exact same contract as app/agent/
tools/billing_tools.py. See that file's docstring for the full rationale
(tenant_id never in input_schema, unit-of-work via db_session()).

Consolidation note: app/services/migration_ai_copilot.py previously also
had natural_language_query, a hardcoded keyword router (not an LLM) over
real session/duplicate data. It's gone, not converted -- get_migration_
session_summary below exposes the same real facts it used to wrap in
canned response text directly as a tool; the consolidated orchestrator's
own model call now does the narration a keyword router doesn't need to.
The other three functions (analyze_data_quality, analyze_error_root_cause,
suggest_cleansing_rules) were already real and are wrapped as-is.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.agent.tools.base import ToolDefinition
from app.core.database import db_session
from app.services.migration_ai_copilot import MigrationAICopilotService
from app.services.agent_adapters.base import agent_tool

_SESSION_ID_PROPERTY = {"type": "string", "format": "uuid"}


_GET_SESSION_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"session_id": _SESSION_ID_PROPERTY},
    "required": ["session_id"],
}


@agent_tool
async def handle_get_migration_session_summary(
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> dict[str, Any]:
    async with db_session() as db:
        return await MigrationAICopilotService.get_session_summary(db, tenant_id, session_id)


_ANALYZE_DATA_QUALITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"session_id": _SESSION_ID_PROPERTY},
    "required": ["session_id"],
}


@agent_tool
async def handle_analyze_migration_data_quality(
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> dict[str, Any]:
    async with db_session() as db:
        report = await MigrationAICopilotService.analyze_data_quality(db, tenant_id, session_id)
        return report.model_dump(mode="json")


_SUGGEST_CLEANSING_RULES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"session_id": _SESSION_ID_PROPERTY},
    "required": ["session_id"],
}


@agent_tool
async def handle_suggest_migration_cleansing_rules(
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> dict[str, Any]:
    async with db_session() as db:
        result = await MigrationAICopilotService.suggest_cleansing_rules(db, tenant_id, session_id)
        return result.model_dump(mode="json")


_ANALYZE_ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "error_message": {"type": "string"},
        "row_data": {"type": "object", "description": "The raw row data that failed, as key/value pairs."},
    },
    "required": ["error_message", "row_data"],
}


@agent_tool
async def handle_analyze_migration_error(
    tenant_id: uuid.UUID,
    error_message: str,
    row_data: dict[str, Any],
) -> dict[str, Any]:
    # Pure text/heuristic analysis, no DB access -- tenant_id is still
    # accepted (and injected the same way as every other tool) for
    # consistency, even though this particular handler doesn't use it.
    del tenant_id
    result = MigrationAICopilotService.analyze_error_root_cause(error_message, row_data)
    return result.model_dump(mode="json")


MIGRATION_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="get_migration_session_summary",
        description="Real record counts (total/imported/invalid) and duplicate count for a migration session.",
        input_schema=_GET_SESSION_SUMMARY_SCHEMA,
        required_permission=("Migration", "System", "Read"),
        handler=handle_get_migration_session_summary,
    ),
    ToolDefinition(
        name="analyze_migration_data_quality",
        description="Health/risk score and quality issue breakdown (format issues, duplicates) for a migration session.",
        input_schema=_ANALYZE_DATA_QUALITY_SCHEMA,
        required_permission=("Migration", "System", "Read"),
        handler=handle_analyze_migration_data_quality,
    ),
    ToolDefinition(
        name="suggest_migration_cleansing_rules",
        description="Real, data-driven cleansing suggestions (merge duplicates, normalize phone format) for a migration session.",
        input_schema=_SUGGEST_CLEANSING_RULES_SCHEMA,
        required_permission=("Migration", "System", "Read"),
        handler=handle_suggest_migration_cleansing_rules,
    ),
    ToolDefinition(
        name="analyze_migration_error",
        description="Root-cause analysis for a single migration row error -- suggested fix, impact, and whether retrying is recommended.",
        input_schema=_ANALYZE_ERROR_SCHEMA,
        required_permission=("Migration", "System", "Read"),
        handler=handle_analyze_migration_error,
    ),
]
