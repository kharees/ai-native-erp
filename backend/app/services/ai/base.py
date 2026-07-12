"""
app/services/ai/base.py
========================
Provider-agnostic interface for LLM calls.

This is the AI Foundation: a real, swappable abstraction over OpenAI and
Anthropic (app/services/ai/openai_provider.py, anthropic_provider.py),
selected via app/services/ai/factory.py:get_ai_provider(). Nothing in this
sprint builds a specific AI *feature* (forecasting, document extraction,
analytics) on top of it — those are explicitly deferred. What exists here
is the plumbing a feature would use, plus one concrete, narrowly-scoped
consumer (migration duplicate detection, see app/services/migration_ai_copilot.py)
that replaces a hardcoded fake number with a real deterministic algorithm —
not an LLM call, since duplicate detection doesn't need one and forcing an
LLM in just to exercise this abstraction would be scope creep into
"Document AI" territory this sprint explicitly excludes.

Design choices
--------------
* Async only — every call site in this codebase is an async FastAPI route
  or an async Celery task wrapper; a sync provider would need its own
  thread-pool dance at every call site instead of once here.
* No silent fallback: if a provider isn't configured (no API key) or the
  underlying SDK call fails, this raises AIProviderError /
  AIProviderNotConfiguredError. A future feature built on this must handle
  that explicitly (e.g. return a 503, or a clear "AI unavailable" state) —
  it must never catch this and substitute fabricated data, which is the
  exact failure mode #28 documents across the existing mocked services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict


class AIMessage(TypedDict):
    role: str  # "user" | "assistant"
    content: str


class AIProviderError(Exception):
    """Raised when an AI provider call fails (network, API error, bad response)."""


class AIProviderNotConfiguredError(AIProviderError):
    """Raised when the selected provider has no API key configured."""


class AIProvider(ABC):
    """Common interface every concrete provider (OpenAI, Anthropic) implements."""

    name: str

    @abstractmethod
    async def complete(
        self,
        messages: list[AIMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """
        Send a chat-style completion request and return the model's text
        response.

        Parameters
        ----------
        messages:
            Conversation turns, each `{"role": "user"|"assistant", "content": str}`.
        system:
            Optional system prompt, passed via whatever mechanism the
            underlying provider uses (a top-level `system` message for
            OpenAI, a dedicated `system` parameter for Anthropic).
        max_tokens:
            Upper bound on the response length.
        temperature:
            Sampling temperature, 0-1 for both providers' APIs.

        Raises
        ------
        AIProviderError
            On any failure — network, auth, rate limit, malformed response.
        """
        raise NotImplementedError
