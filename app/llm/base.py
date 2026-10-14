"""Tipos neutrales del agente: ningún módulo fuera de app/llm/ conoce un SDK de proveedor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]
    provider_id: str | None = None  # id que asignó el proveedor (puede no existir)


@dataclass
class ToolResult:
    call_id: str
    name: str
    content: dict[str, Any]
    is_error: bool = False
    provider_id: str | None = None


@dataclass
class Message:
    role: Literal["user", "assistant", "tool"]
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    provider: str | None = None
    raw: Any = None  # contenido nativo del proveedor, para reenviarlo intacto


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens + self.thinking_tokens

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.thinking_tokens + other.thinking_tokens,
        )


@dataclass
class LLMResponse:
    message: Message
    usage: Usage
    finish_reason: str | None = None


class LLMError(Exception):
    """Fallo del proveedor ya clasificado. `retryable` = es seguro reintentar (nada se ejecutó)."""

    def __init__(self, kind: str, message: str = "", retryable: bool = False):
        super().__init__(f"{kind}: {message}" if message else kind)
        self.kind = kind
        self.retryable = retryable


class LLMClient(Protocol):
    provider: str
    model: str
    configured: bool

    def generate(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSpec],
        timeout_s: float,
        tool_choice: Literal["auto", "none"] = "auto",
    ) -> LLMResponse: ...
