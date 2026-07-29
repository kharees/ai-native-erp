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

complete_with_tools() (added for the Billing orchestrator, see
app/agent/orchestrator/) is native tool-calling, not prompted-JSON --
each provider maps ToolDefinition-shaped tools onto its own SDK's actual
tools= parameter and parses its own native tool-call response format.
Deliberately not built on top of complete()'s plain-text interface: both
providers are specifically trained for structured tool-calling through
this path, and prompted-JSON extraction is measurably less reliable for
a tool like create_invoice with a nested items array -- not a risk worth
taking for tools that create invoices and record payments.

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
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict


class AITextBlock(TypedDict):
    type: Literal["text"]
    text: str


class AIImageBlock(TypedDict):
    """data is raw base64 (no "data:" URL prefix, no whitespace/newlines --
    each provider's translator wraps it in whatever envelope that
    provider's wire format needs)."""
    type: Literal["image"]
    media_type: str  # e.g. "image/jpeg", "image/png"
    data: str


AIContentBlock = AITextBlock | AIImageBlock


class AIToolCall(TypedDict):
    """One tool invocation the model requested. `arguments` is already a
    parsed dict -- OpenAI returns its arguments as a JSON string on the
    wire; providers are responsible for parsing that before this type is
    ever constructed, so callers never handle provider-specific encoding."""
    id: str
    name: str
    arguments: dict[str, Any]


class AIMessage(TypedDict, total=False):
    """
    One conversation turn. `total=False` so this single type can represent
    all three roles a tool-calling conversation needs without a Union:

    - Plain text turn (the only shape used before complete_with_tools
      existed, and the only shape complete() ever needs):
        {"role": "user" | "assistant", "content": "..."}
    - An assistant turn that invoked one or more tools (must be replayed
      back to the provider verbatim on the next turn -- both providers
      require their own prior tool-call turn in the message history to
      make sense of the tool-result turns that follow it):
        {"role": "assistant", "content": "optional preamble text" | None,
         "tool_calls": [AIToolCall, ...]}
    - A tool-result turn answering one specific prior tool call by id:
        {"role": "tool_result", "tool_call_id": "...", "content": "..."}

    role/content stay required-in-practice for the plain-text case
    (existing callers always set both); tool_calls and tool_call_id are
    the only genuinely optional keys, present on exactly one of the two
    new turn shapes above.

    content also accepts list[AIContentBlock] (a mix of AITextBlock/
    AIImageBlock) instead of a plain str, for multimodal turns:
        {"role": "user", "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image", "media_type": "image/jpeg", "data": "<base64>"},
        ]}
    Only meaningful on plain user/assistant turns (the ones handled by
    this docstring's first bullet) -- tool_calls/tool_result turns don't
    carry images in this codebase; each provider's translator only looks
    for list-shaped content on that plain-turn branch.
    """
    role: str
    content: str | list[AIContentBlock] | None
    tool_calls: list[AIToolCall]
    tool_call_id: str


def message_has_image(messages: list[AIMessage]) -> bool:
    """True if any message's content contains an image block. Shared
    across all three providers' complete()/complete_with_tools() so each
    can refuse up front (AIProviderError, not a silent drop) when its
    configured model doesn't support vision -- see each provider's own
    _model_supports_vision()."""
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            if any(isinstance(block, dict) and block.get("type") == "image" for block in content):
                return True
    return False


@dataclass
class AIToolCallResult:
    """Result of a complete_with_tools() call. Exactly one of `text` /
    `tool_calls` is meaningful in practice: a provider returns tool_calls
    when it decided to act, or text when it produced a final answer --
    never both empty (that raises AIProviderError, same no-silent-fallback
    contract as complete())."""
    text: str | None
    tool_calls: list[AIToolCall] = field(default_factory=list)


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

    @abstractmethod
    async def complete_with_tools(
        self,
        messages: list[AIMessage],
        tools: list[dict[str, Any]],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AIToolCallResult:
        """
        Send a chat-style completion request with tools the model may
        invoke, and return either its final text or the tool call(s) it
        wants to make.

        Parameters
        ----------
        messages:
            Conversation turns — see AIMessage. May include prior
            assistant tool-call turns and tool-result turns from earlier
            iterations of an orchestrator loop, not just plain text.
        tools:
            `[{"name": str, "description": str, "input_schema": dict}, ...]`
            — the same shape as app.agent.tools.billing_tools.ToolDefinition's
            name/description/input_schema fields, so callers pass tool
            definitions through with no reshaping. Each provider maps this
            onto its own SDK's native tools= parameter internally.
        system, max_tokens, temperature:
            Same as complete().

        Raises
        ------
        AIProviderError
            On any failure — network, auth, rate limit, or a response with
            neither text nor tool_calls (a provider returning genuinely
            nothing is treated as a failure, not an empty success).
        """
        raise NotImplementedError
