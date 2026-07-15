"""
app/services/ai/anthropic_provider.py
========================================
Anthropic implementation of the AIProvider interface.
"""

from __future__ import annotations

from typing import Any

import structlog
from anthropic import AsyncAnthropic, APIError, APIConnectionError, AuthenticationError

from app.services.ai.base import AIMessage, AIProvider, AIProviderError, AIToolCall, AIToolCallResult

log = structlog.get_logger(__name__)


def _to_anthropic_messages(messages: list[AIMessage]) -> list[dict[str, Any]]:
    """Translates the provider-agnostic AIMessage list (see base.py) into
    Anthropic's wire format. The two non-trivial cases:

    - An assistant turn that made tool calls becomes a content-block list
      (optional text block + one tool_use block per call), not a plain
      string -- Anthropic's own prior turn must be replayed in exactly the
      shape it was originally returned in for the API to accept it.
    - A "tool_result" turn (this codebase's role, not Anthropic's) becomes
      a *user*-role message containing a tool_result content block --
      Anthropic has no separate "tool" role; tool results are user turns
      by convention.
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        if role == "assistant" and msg.get("tool_calls"):
            content: list[dict[str, Any]] = []
            if msg.get("content"):
                content.append({"type": "text", "text": msg["content"]})
            for call in msg["tool_calls"]:
                content.append({"type": "tool_use", "id": call["id"], "name": call["name"], "input": call["arguments"]})
            out.append({"role": "assistant", "content": content})
        elif role == "tool_result":
            out.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": msg["tool_call_id"], "content": msg.get("content") or ""}],
            })
        else:
            out.append({"role": role, "content": msg.get("content") or ""})
    return out


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(
        self,
        messages: list[AIMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        try:
            response = await self._client.messages.create(
                model=self._model,
                system=system or "",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except AuthenticationError as exc:
            log.error("anthropic_auth_failed", error=str(exc))
            raise AIProviderError("Anthropic authentication failed — check ANTHROPIC_API_KEY.") from exc
        except APIConnectionError as exc:
            log.error("anthropic_connection_failed", error=str(exc))
            raise AIProviderError("Could not reach Anthropic.") from exc
        except APIError as exc:
            log.error("anthropic_api_error", error=str(exc))
            raise AIProviderError(f"Anthropic API error: {exc}") from exc

        if not response.content:
            raise AIProviderError("Anthropic returned an empty response.")

        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        if not text_blocks:
            raise AIProviderError("Anthropic response contained no text content.")
        return "".join(text_blocks)

    async def complete_with_tools(
        self,
        messages: list[AIMessage],
        tools: list[dict[str, Any]],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AIToolCallResult:
        # tools is already {"name", "description", "input_schema"} per
        # entry — Anthropic's own native tools= shape, no translation needed.
        try:
            response = await self._client.messages.create(
                model=self._model,
                system=system or "",
                messages=_to_anthropic_messages(messages),
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except AuthenticationError as exc:
            log.error("anthropic_auth_failed", error=str(exc))
            raise AIProviderError("Anthropic authentication failed — check ANTHROPIC_API_KEY.") from exc
        except APIConnectionError as exc:
            log.error("anthropic_connection_failed", error=str(exc))
            raise AIProviderError("Could not reach Anthropic.") from exc
        except APIError as exc:
            log.error("anthropic_api_error", error=str(exc))
            raise AIProviderError(f"Anthropic API error: {exc}") from exc

        if not response.content:
            raise AIProviderError("Anthropic returned an empty response.")

        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        tool_use_blocks = [block for block in response.content if getattr(block, "type", None) == "tool_use"]

        if not text_blocks and not tool_use_blocks:
            raise AIProviderError("Anthropic response contained neither text nor a tool call.")

        tool_calls: list[AIToolCall] = [
            AIToolCall(id=block.id, name=block.name, arguments=block.input) for block in tool_use_blocks
        ]
        return AIToolCallResult(text="".join(text_blocks) if text_blocks else None, tool_calls=tool_calls)
