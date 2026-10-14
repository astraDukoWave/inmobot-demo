"""Adaptador de Claude (Messages API con tools).

Estado: PENDIENTE DE VALIDACIÓN REAL. Solo tiene pruebas con objetos simulados del SDK; no se ha corrido contra
la API de Anthropic (ver README). Se activa con LLM_PROVIDER=anthropic y ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from .base import LLMError, LLMResponse, Message, ToolCall, ToolSpec, Usage


class AnthropicLLM:
    provider = "anthropic"
    validated_against_real_api = False

    def __init__(self, api_key: str | None, model: str, client: Any = None):
        self.model = model
        self.configured = bool(api_key) or client is not None
        self._client = client
        if self._client is None and api_key:
            import anthropic

            self._client = anthropic.Anthropic(api_key=api_key, max_retries=0)

    def to_messages(self, messages: list[Message]) -> list[dict]:
        out: list[dict] = []

        def push(role: str, blocks: list[dict]) -> None:
            if out and out[-1]["role"] == role:  # la API pide alternar roles: se fusionan consecutivos
                out[-1]["content"].extend(blocks)
            else:
                out.append({"role": role, "content": blocks})

        for m in messages:
            if m.role == "user":
                push("user", [{"type": "text", "text": m.text}])
            elif m.role == "assistant":
                blocks = [{"type": "text", "text": m.text}] if m.text else []
                blocks += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.args} for c in m.tool_calls]
                if blocks:
                    push("assistant", blocks)
            elif m.role == "tool":
                push("user", [{"type": "tool_result", "tool_use_id": r.call_id, "is_error": r.is_error,
                               "content": json.dumps(r.content, ensure_ascii=False)} for r in m.tool_results])
        return out

    def generate(self, *, system: str, messages: list[Message], tools: list[ToolSpec], timeout_s: float,
                 tool_choice: Literal["auto", "none"] = "auto") -> LLMResponse:
        if not self.configured:
            raise LLMError("not_configured", "falta ANTHROPIC_API_KEY")
        import anthropic

        kwargs: dict[str, Any] = {
            "model": self.model, "max_tokens": 1024, "system": system, "messages": self.to_messages(messages),
            "timeout": timeout_s,
        }
        if tools:
            kwargs["tools"] = [{"name": t.name, "description": t.description, "input_schema": t.input_schema}
                               for t in tools]
            kwargs["tool_choice"] = {"type": tool_choice}
        try:
            resp = self._client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            raise LLMError("rate_limited", "429", retryable=True) from exc
        except anthropic.APITimeoutError as exc:
            raise LLMError("timeout", "timeout") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("network", "connection", retryable=True) from exc
        except anthropic.APIStatusError as exc:
            code = exc.status_code
            raise LLMError("server_error" if code >= 500 else "bad_request", str(code),
                           retryable=code >= 500) from exc
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        calls = [ToolCall(id=b.id, name=b.name, args=dict(b.input or {}), provider_id=b.id)
                 for b in resp.content if b.type == "tool_use"]
        usage = Usage(resp.usage.input_tokens or 0, resp.usage.output_tokens or 0)
        return LLMResponse(Message(role="assistant", text=text, tool_calls=calls, provider=self.provider),
                           usage, resp.stop_reason)
