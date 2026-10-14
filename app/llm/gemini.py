"""Adaptador de Gemini (google-genai, generate_content, tool use manual).

Clave de corrección: el contenido que devuelve el modelo se reenvía INTACTO en el historial, porque puede traer
`thought_signature` en las partes de function_call; reconstruirlo desde texto rompe el turno con tools.
"""

from __future__ import annotations

import itertools
import math
from typing import Any, Literal

import httpx
from google import genai
from google.genai import errors, types

from .base import LLMError, LLMResponse, Message, ToolCall, ToolSpec, Usage

# El SDK manda el timeout como deadline del servidor (header X-Server-Timeout = ceil(timeout)). Con 9 s la API
# respondió 400 inmediato en todas las llamadas (live-smoke 3/3); con 20 s funcionó (1/3 y 2/3). Por eso el
# deadline del servidor nunca baja de 10 s, mientras el tope real lo pone el cliente (httpx) con el valor del agente.
MIN_SERVER_TIMEOUT_S = 10
_BLOCKED = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"}
_ids = itertools.count(1)


class GeminiLLM:
    provider = "gemini"

    def __init__(self, api_key: str | None, model: str, thinking_level: str = "low", client: Any = None):
        self.model = model
        self.thinking_level = thinking_level
        self.configured = bool(api_key) or client is not None
        self._client = client
        if self._client is None and api_key:
            # Sin reintentos del SDK: el agente controla el deadline total del turno (A5).
            self._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
            )

    # --- conversión neutral → Gemini ---------------------------------------------------------------------
    def to_contents(self, messages: list[Message]) -> list[types.Content]:
        contents: list[types.Content] = []
        for m in messages:
            if m.role == "user":
                contents.append(types.Content(role="user", parts=[types.Part(text=m.text)]))
            elif m.role == "assistant":
                if m.provider == self.provider and m.raw is not None:
                    contents.append(m.raw)  # intacto: conserva thought signatures
                    continue
                parts = [types.Part(text=m.text)] if m.text else []
                parts += [types.Part(function_call=types.FunctionCall(id=c.provider_id, name=c.name, args=c.args))
                          for c in m.tool_calls]
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
            elif m.role == "tool":
                parts = [
                    types.Part(function_response=types.FunctionResponse(
                        id=r.provider_id, name=r.name,
                        response={"error": r.content} if r.is_error else {"output": r.content}))
                    for r in m.tool_results
                ]
                contents.append(types.Content(role="user", parts=parts))
        return contents

    def build_config(self, system: str, tools: list[ToolSpec], timeout_s: float,
                     tool_choice: Literal["auto", "none"]) -> types.GenerateContentConfig:
        declarations = [types.FunctionDeclaration(name=t.name, description=t.description,
                                                  parameters_json_schema=t.input_schema) for t in tools]
        mode = types.FunctionCallingConfigMode.NONE if tool_choice == "none" else types.FunctionCallingConfigMode.AUTO
        return types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=declarations)] if declarations else None,
            tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode=mode))
            if declarations else None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            automatic_continuation=False,  # 1 llamada = 1 petición HTTP; si no, A5 se rompe (hallazgo H3)
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            max_output_tokens=2048,
            http_options=types.HttpOptions(
                timeout=max(1000, int(timeout_s * 1000)),
                headers={"X-Server-Timeout": str(max(MIN_SERVER_TIMEOUT_S, math.ceil(timeout_s)))},
                retry_options=types.HttpRetryOptions(attempts=1)),
        )

    # --- llamada -----------------------------------------------------------------------------------------
    def generate(self, *, system: str, messages: list[Message], tools: list[ToolSpec], timeout_s: float,
                 tool_choice: Literal["auto", "none"] = "auto") -> LLMResponse:
        if not self.configured:
            raise LLMError("not_configured", "falta GEMINI_API_KEY")
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=self.to_contents(messages),
                config=self.build_config(system, tools, timeout_s, tool_choice))
        except errors.APIError as exc:
            code = getattr(exc, "code", None) or 0
            if code == 429:
                raise LLMError("rate_limited", str(code), retryable=True) from exc
            if code >= 500:
                status = getattr(exc, "status", None) or ""
                raise LLMError("server_error", f"{code} {status}".strip(), retryable=True) from exc
            if code in (401, 403):
                raise LLMError("auth", str(code)) from exc
            detail = f"{code} {getattr(exc, 'status', '') or ''} {(getattr(exc, 'message', '') or '')[:120]}"
            raise LLMError("bad_request", " ".join(detail.split())) from exc
        except httpx.TimeoutException as exc:
            # generate_content no tiene efectos de nuestro lado: reintentar es seguro si queda tiempo.
            raise LLMError("timeout", type(exc).__name__, retryable=True) from exc
        except httpx.HTTPError as exc:
            raise LLMError("network", type(exc).__name__, retryable=True) from exc
        except ValueError as exc:  # respuesta 200 que no es JSON o no valida contra el SDK
            raise LLMError("bad_response", type(exc).__name__, retryable=True) from exc
        try:
            return self.parse(response)
        except (ValueError, AttributeError, TypeError) as exc:
            raise LLMError("bad_response", type(exc).__name__, retryable=True) from exc

    def parse(self, response: types.GenerateContentResponse) -> LLMResponse:
        um = response.usage_metadata
        usage = Usage(
            input_tokens=(um.prompt_token_count or 0) if um else 0,
            output_tokens=(um.candidates_token_count or 0) if um else 0,
            thinking_tokens=(um.thoughts_token_count or 0) if um else 0,
        )
        candidate = response.candidates[0] if response.candidates else None
        finish = None
        if candidate is not None and candidate.finish_reason is not None:
            finish = getattr(candidate.finish_reason, "value", str(candidate.finish_reason))
        if candidate is None or candidate.content is None or finish in _BLOCKED:
            return LLMResponse(Message(role="assistant", provider=self.provider), usage, finish or "EMPTY")
        parts = candidate.content.parts or []
        text = "".join(p.text for p in parts if p.text and not p.thought).strip()
        calls = []
        for p in parts:
            if p.function_call is not None and p.function_call.name:
                fc = p.function_call
                calls.append(ToolCall(id=fc.id or f"gem_{next(_ids)}", name=fc.name, args=dict(fc.args or {}),
                                      provider_id=fc.id))
        message = Message(role="assistant", text=text, tool_calls=calls, provider=self.provider,
                          raw=candidate.content)
        return LLMResponse(message, usage, finish)
