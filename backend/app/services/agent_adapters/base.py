"""
app/services/agent_adapters/base.py
====================================
Sprint 5 (#2, audit #6): structural guard preventing AsyncSession from ever
reaching a function meant to be exposed as an AI tool.

Why this exists
----------------
Every function in app/crud and most of app/services takes `db: AsyncSession`
as a parameter — correct for the internal application layer (see
docs/production-hardening.md and the Sprint 5 #1 unit-of-work refactor,
which depends on callers within one request sharing one session for
atomicity). But an AsyncSession must never be handed to an LLM tool-calling
schema: it isn't JSON-serializable, isn't something a model can meaningfully
fill in as an argument, and handing a live DB session to code an LLM's
output indirectly influences is a real safety boundary, not a style
preference (see docs/ai-foundation.md's AI tool-calling readiness section).

`@agent_tool` is the enforcement point. Every function intended to be
callable by an agent (now or once a tool registry exists — see
docs/ai-foundation.md, "Nothing built on top of the abstraction yet") must
be wrapped with it. The decorator inspects the function's signature at
*definition time* (i.e. at import) and raises immediately if any parameter
is annotated AsyncSession/AsyncConnection or named `db`/`session` — so a
mistake here fails the moment the module is imported, not the first time an
agent happens to call it.

This does not build a tool registry, JSON-schema generator, or orchestrator
— those are the actual "AI OS layer" (audit #3, explicitly separate,
larger, not-yet-built work). This is the narrower, structural precondition
that work will need: a set of adapter functions that are safe to register
as tools in the first place.
"""

from __future__ import annotations

import functools
import inspect
from typing import Callable, TypeVar

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

F = TypeVar("F", bound=Callable)

_FORBIDDEN_PARAM_NAMES = {"db", "session", "db_session", "connection", "conn"}
_FORBIDDEN_ANNOTATIONS = (AsyncSession, AsyncConnection)


class AgentToolSignatureError(TypeError):
    """Raised at import time when a function decorated with @agent_tool
    exposes a database session/connection in its public signature."""


def agent_tool(func: F) -> F:
    """
    Marks `func` as safe for AI tool-calling exposure and enforces it.

    Requirements checked on every parameter of the wrapped function:
      - annotation is not AsyncSession or AsyncConnection (by isinstance-of
        type check, so subclasses are also caught)
      - parameter name is not one of the conventional session-parameter
        names (db, session, db_session, connection, conn) — catches the
        unannotated case too

    Raises AgentToolSignatureError immediately (at module import time, not
    call time) if either check fails, so a mistake here breaks app startup
    loudly instead of silently shipping a tool an agent could use to smuggle
    a raw session reference into its own output.
    """
    signature = inspect.signature(func)
    for name, param in signature.parameters.items():
        if name in _FORBIDDEN_PARAM_NAMES:
            raise AgentToolSignatureError(
                f"@agent_tool {func.__module__}.{func.__qualname__}: parameter "
                f"'{name}' is a forbidden session-shaped name. Agent tools must "
                f"open their own session internally (see db_session() in "
                f"app.core.database) and never accept one from the caller."
            )
        annotation = param.annotation
        if isinstance(annotation, type) and issubclass(annotation, _FORBIDDEN_ANNOTATIONS):
            raise AgentToolSignatureError(
                f"@agent_tool {func.__module__}.{func.__qualname__}: parameter "
                f"'{name}' is annotated {annotation!r}. Agent-tool functions "
                f"must never accept a database session/connection as an argument."
            )

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    wrapper.__agent_tool__ = True
    return wrapper  # type: ignore[return-value]
