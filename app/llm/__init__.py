"""Fábrica de proveedores. El resto del código solo ve LLMClient."""

from __future__ import annotations

from ..config import Settings
from .base import LLMClient, LLMError, LLMResponse, Message, ToolCall, ToolResult, ToolSpec, Usage


def build_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "anthropic":
        from .anthropic import AnthropicLLM

        return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model)
    if settings.llm_provider == "fake":
        from .fake import FakeLLM

        return FakeLLM()
    from .gemini import GeminiLLM

    return GeminiLLM(settings.gemini_api_key, settings.gemini_model, settings.gemini_thinking_level)


__all__ = ["LLMClient", "LLMError", "LLMResponse", "Message", "ToolCall", "ToolResult", "ToolSpec", "Usage",
           "build_llm"]
