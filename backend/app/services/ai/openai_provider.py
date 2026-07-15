"""
app/services/ai/openai_provider.py
====================================
OpenAI implementation of the AIProvider interface.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from openai import AsyncOpenAI, APIError, APIConnectionError, AuthenticationError

from app.services.ai.base import AIMessage, AIProvider, AIProviderError, AIToolCall, AIToolCallResult

log = structlog.get_logger(__name__)


def _to_openai_messages(messages: list[AIMessage]) -> list[dict[str, Any]]:
    """Translates the provider-agnostic AIMessage list (see base.py) into
    OpenAI's wire format. The two non-trivial cases:

    - An assistant turn that made tool calls carries a `tool_calls` list
      alongside (possibly None) `content` -- and each call's arguments
      must be a JSON *string* on the wire, not the dict this codebase
      works with everywhere else (OpenAI's own tool_calls response later
      comes back the same way, parsed back into a dict in
      complete_with_tools below).
    - A "tool_result" turn (this codebase's role, not OpenAI's) becomes a
      `role: "tool"` message referencing tool_call_id -- OpenAI does have
      a dedicated tool role, unlike Anthropic.
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        if role == "assistant" and msg.get("tool_calls"):
            out.append({
                "role": "assistant",
                "content": msg.get("content"),
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {"name": call["name"], "arguments": json.dumps(call["arguments"])},
                    }
                    for call in msg["tool_calls"]
                ],
            })
        elif role == "tool_result":
            out.append({"role": "tool", "tool_call_id": msg["tool_call_id"], "content": msg.get("content") or ""})
        else:
            out.append({"role": role, "content": msg.get("content") or ""})
    return out


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(
        self,
        messages: list[AIMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        openai_messages.extend(messages)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except AuthenticationError as exc:
            log.error("openai_auth_failed", error=str(exc))
            raise AIProviderError("OpenAI authentication failed — check OPENAI_API_KEY.") from exc
        except APIConnectionError as exc:
            log.error("openai_connection_failed", error=str(exc))
            raise AIProviderError("Could not reach OpenAI.") from exc
        except APIError as exc:
            log.error("openai_api_error", error=str(exc))
            raise AIProviderError(f"OpenAI API error: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            raise AIProviderError("OpenAI returned an empty response.")
        return content

    async def complete_with_tools(
        self,
        messages: list[AIMessage],
        tools: list[dict[str, Any]],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AIToolCallResult:
        # tools arrives as {"name", "description", "input_schema"} per
        # entry (Anthropic's native shape, shared across providers per
        # base.py's docstring) -- wrap each into OpenAI's function-call shape.
        openai_tools = [
            {
                "type": "function",
                "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]},
            }
            for t in tools
        ]

        openai_messages: list[dict[str, Any]] = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        openai_messages.extend(_to_openai_messages(messages))

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                tools=openai_tools,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except AuthenticationError as exc:
            log.error("openai_auth_failed", error=str(exc))
            raise AIProviderError("OpenAI authentication failed — check OPENAI_API_KEY.") from exc
        except APIConnectionError as exc:
            log.error("openai_connection_failed", error=str(exc))
            raise AIProviderError("Could not reach OpenAI.") from exc
        except APIError as exc:
            log.error("openai_api_error", error=str(exc))
            raise AIProviderError(f"OpenAI API error: {exc}") from exc

        message = response.choices[0].message
        raw_tool_calls = message.tool_calls or []

        if not message.content and not raw_tool_calls:
            raise AIProviderError("OpenAI response contained neither text nor a tool call.")

        tool_calls: list[AIToolCall] = []
        for call in raw_tool_calls:
            try:
                arguments = json.loads(call.function.arguments)
            except json.JSONDecodeError as exc:
                raise AIProviderError(
                    f"OpenAI returned malformed JSON arguments for tool '{call.function.name}': {exc}"
                ) from exc
            tool_calls.append(AIToolCall(id=call.id, name=call.function.name, arguments=arguments))

        return AIToolCallResult(text=message.content, tool_calls=tool_calls)
