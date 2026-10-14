"""LLM falso y guionado: pruebas y CI sin red ni keys. No es un modelo: repite el guion que le dan."""

from __future__ import annotations

import itertools
from collections.abc import Callable
from typing import Literal

from .base import LLMResponse, Message, ToolCall, ToolSpec, Usage

Step = LLMResponse | Exception | Callable[[list[Message]], LLMResponse]
_ids = itertools.count(1)


def text(reply: str, tokens: int = 10) -> LLMResponse:
    return LLMResponse(Message(role="assistant", text=reply, provider="fake"), Usage(tokens, tokens // 2))


def tool(name: str, args: dict | None = None, reply: str = "", tokens: int = 10) -> LLMResponse:
    call = ToolCall(id=f"fake_{next(_ids)}", name=name, args=args or {})
    return LLMResponse(Message(role="assistant", text=reply, tool_calls=[call], provider="fake"),
                       Usage(tokens, tokens // 2))


class FakeLLM:
    provider = "fake"
    model = "fake-scripted"
    configured = True

    def __init__(self, script: list[Step] | None = None,
                 default_reply: str = "Modo demo sin modelo: configura LLM_PROVIDER y su API key."):
        self.script = list(script or [])
        self.default_reply = default_reply
        self.calls: list[dict] = []

    def generate(self, *, system: str, messages: list[Message], tools: list[ToolSpec], timeout_s: float,
                 tool_choice: Literal["auto", "none"] = "auto") -> LLMResponse:
        self.calls.append({"system": system, "messages": list(messages), "tools": [t.name for t in tools],
                           "timeout_s": timeout_s, "tool_choice": tool_choice})
        if not self.script:
            return text(self.default_reply)
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        if callable(step):
            return step(messages)
        return step
