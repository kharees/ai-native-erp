"""
app/agent/orchestrator/
=========================
The tool-calling loop for the AI OS layer (audit #3), built on
app/services/ai/base.py's complete_with_tools() and app/agent/tools/.
See loop.py for the implementation; this module just re-exports the
public entry points.
"""

from app.agent.orchestrator.loop import (
    DEFAULT_MAX_ITERATIONS,
    OrchestratorResult,
    ToolOutcome,
    resume_after_confirmation,
    run_turn,
)

__all__ = [
    "run_turn",
    "resume_after_confirmation",
    "OrchestratorResult",
    "ToolOutcome",
    "DEFAULT_MAX_ITERATIONS",
]
