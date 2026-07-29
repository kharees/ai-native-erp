"""
app/services/ai/gemini_provider.py
=====================================
Gemini (Google AI Studio) implementation of the AIProvider interface.

Unlike anthropic_provider.py/openai_provider.py, this does not use Google's
official google-genai SDK -- every version of it requires httpx>=0.28.1 and
either pydantic>=2.12.5 or websockets>=13.0, all of which conflict with the
versions this repo pins (httpx==0.27.0, pydantic==2.7.0). Installing it was
tried and confirmed to silently upgrade both and break 22 existing tests.
Calling the REST API directly via httpx (already a pinned, tested dependency
here) avoids the conflict entirely, at the cost of owning the wire-format
translation ourselves -- the same role _to_anthropic_messages/
_to_openai_messages already play for the other two providers.

Wire format notes
------------------
* Gemini's `contents` roles are "user" and "model" (not "assistant") --
  both prior user turns and prior assistant/tool-call turns map onto these.
* A function call the model made becomes a `functionCall` part in a
  "model"-role content entry; the corresponding result must be sent back as
  a `functionResponse` part in the *next* "user"-role entry -- Gemini has no
  separate "tool" role.
* functionResponse matches its functionCall by *name*, not by an opaque call
  id -- Gemini's contents history has no id concept at all. This codebase's
  tool_result AIMessage only carries tool_call_id (sufficient for Anthropic/
  OpenAI, which do match by id), so _to_gemini_contents rebuilds an
  id -> name map by walking the message list in order, populated whenever it
  sees an assistant/tool_calls turn and consumed by the tool_result turn(s)
  that follow it. This is purely a Gemini-translation-layer concern; it does
  not change AIMessage/AIToolCall, so Anthropic/OpenAI are unaffected.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.services.ai.base import AIMessage, AIProvider, AIProviderError, AIToolCall, AIToolCallResult, message_has_image

log = structlog.get_logger(__name__)

_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Best-effort denylist of known text-only Gemini models -- err toward NOT
# rejecting an unlisted/newer model name (a real API-level error on a
# genuinely non-vision model is an acceptable fallback; incorrectly
# blocking a real vision-capable model is not). Every current Gemini model
# is natively multimodal; only the legacy PaLM2-era Bison models (accessed
# through this same v1beta REST surface for backward compatibility) never
# supported images.
_NON_VISION_MODEL_MARKERS = ("bison", "gecko")


def _model_supports_vision(model: str) -> bool:
    lowered = model.lower()
    return not any(marker in lowered for marker in _NON_VISION_MODEL_MARKERS)


def _to_gemini_parts(content: str | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if isinstance(content, list):
        parts = []
        for block in content:
            if block["type"] == "image":
                parts.append({"inline_data": {"mime_type": block["media_type"], "data": block["data"]}})
            else:
                parts.append({"text": block["text"]})
        return parts
    return [{"text": content or ""}]


def _to_gemini_contents(messages: list[AIMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    call_id_to_name: dict[str, str] = {}

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "assistant" and msg.get("tool_calls"):
            parts: list[dict[str, Any]] = []
            if content:
                parts.append({"text": content})
            for call in msg["tool_calls"]:
                call_id_to_name[call["id"]] = call["name"]
                parts.append({"functionCall": {"name": call["name"], "args": call["arguments"]}})
            out.append({"role": "model", "parts": parts})
        elif role == "tool_result":
            name = call_id_to_name.get(msg["tool_call_id"], "")
            out.append({
                "role": "user",
                "parts": [{"functionResponse": {"name": name, "response": {"content": content or ""}}}],
            })
        elif role == "assistant":
            out.append({"role": "model", "parts": _to_gemini_parts(content)})
        else:
            out.append({"role": "user", "parts": _to_gemini_parts(content)})
    return out


def _sanitize_schema_for_gemini(schema: dict[str, Any]) -> dict[str, Any]:
    """Gemini's function-calling parameters use a restricted OpenAPI subset
    that rejects unrecognized JSON Schema keywords outright (confirmed live:
    a 400 INVALID_ARGUMENT naming the exact field path) rather than ignoring
    them the way Anthropic/OpenAI do. exclusiveMinimum/exclusiveMaximum are
    the two keywords this codebase's tool schemas actually use that Gemini
    doesn't support -- converted to their inclusive minimum/maximum
    equivalents (a small boundary loosening: >0 becomes >=0) rather than
    dropped outright, so the constraint still reaches the model in some
    form. Recurses into nested object/array schemas (e.g. create_invoice's
    items array) since the same restriction applies at every level.
    """
    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "exclusiveMinimum":
            out["minimum"] = value
        elif key == "exclusiveMaximum":
            out["maximum"] = value
        elif key == "properties" and isinstance(value, dict):
            out[key] = {k: _sanitize_schema_for_gemini(v) for k, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            out[key] = _sanitize_schema_for_gemini(value)
        else:
            out[key] = value
    return out


def _extract_text_and_tool_calls(candidate: dict[str, Any]) -> tuple[str | None, list[AIToolCall]]:
    parts = candidate.get("content", {}).get("parts", [])
    text_chunks = [p["text"] for p in parts if "text" in p]
    tool_calls = [
        AIToolCall(id=f"call_{i}", name=p["functionCall"]["name"], arguments=p["functionCall"].get("args", {}))
        for i, p in enumerate(parts)
        if "functionCall" in p
    ]
    return ("".join(text_chunks) if text_chunks else None), tool_calls


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(timeout=60.0)

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{_API_BASE}/models/{self._model}:generateContent"
        log.debug("gemini_request", url=url, model=self._model, body=body)
        try:
            response = await self._client.post(url, params={"key": self._api_key}, json=body)
        except httpx.ConnectError as exc:
            log.error("gemini_connection_failed", error=str(exc))
            raise AIProviderError("Could not reach Gemini.") from exc
        except httpx.TimeoutException as exc:
            log.error("gemini_timeout", error=str(exc))
            raise AIProviderError("Gemini request timed out.") from exc

        if response.status_code >= 400:
            # Gemini reports an invalid API key as a 400 INVALID_ARGUMENT,
            # not 401/403 -- status code alone can't distinguish "bad key"
            # from "bad request body" (e.g. an unsupported schema keyword).
            # Inspect the body for an auth-specific signal instead of
            # trusting the status code.
            error_status = ""
            error_message = ""
            try:
                error_body = response.json().get("error", {})
                error_status = error_body.get("status", "")
                error_message = error_body.get("message", "")
            except ValueError:
                pass

            if response.status_code in (401, 403) or error_status in ("UNAUTHENTICATED", "PERMISSION_DENIED") or "API key not valid" in error_message:
                log.error("gemini_auth_failed", status=response.status_code, body=response.text)
                raise AIProviderError("Gemini authentication failed — check GEMINI_API_KEY.")

            log.error("gemini_api_error", status=response.status_code, body=response.text)
            raise AIProviderError(f"Gemini API error ({response.status_code}): {response.text}")

        return response.json()

    async def complete(
        self,
        messages: list[AIMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        if message_has_image(messages) and not _model_supports_vision(self._model):
            raise AIProviderError(
                f"Model '{self._model}' does not support image input. "
                f"Configure a vision-capable model (e.g. via AI_MODEL_VISION / "
                f"get_ai_provider(model=...)) to send images."
            )

        body: dict[str, Any] = {
            "contents": _to_gemini_contents(messages),
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        data = await self._post(body)
        candidates = data.get("candidates") or []
        if not candidates:
            reason = data.get("promptFeedback", {}).get("blockReason")
            raise AIProviderError(f"Gemini returned no candidates{f' (blocked: {reason})' if reason else ''}.")

        text, _ = _extract_text_and_tool_calls(candidates[0])
        if not text:
            raise AIProviderError("Gemini response contained no text content.")
        return text

    async def complete_with_tools(
        self,
        messages: list[AIMessage],
        tools: list[dict[str, Any]],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AIToolCallResult:
        if message_has_image(messages) and not _model_supports_vision(self._model):
            raise AIProviderError(
                f"Model '{self._model}' does not support image input. "
                f"Configure a vision-capable model (e.g. via AI_MODEL_VISION / "
                f"get_ai_provider(model=...)) to send images."
            )

        gemini_tools = [{
            "functionDeclarations": [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": _sanitize_schema_for_gemini(t["input_schema"]),
                }
                for t in tools
            ]
        }]

        body: dict[str, Any] = {
            "contents": _to_gemini_contents(messages),
            "tools": gemini_tools,
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        data = await self._post(body)
        candidates = data.get("candidates") or []
        if not candidates:
            reason = data.get("promptFeedback", {}).get("blockReason")
            raise AIProviderError(f"Gemini returned no candidates{f' (blocked: {reason})' if reason else ''}.")

        text, tool_calls = _extract_text_and_tool_calls(candidates[0])
        if not text and not tool_calls:
            raise AIProviderError("Gemini response contained neither text nor a tool call.")
        return AIToolCallResult(text=text, tool_calls=tool_calls)
