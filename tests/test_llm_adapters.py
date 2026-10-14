"""Adaptadores contra objetos reales de los SDK, sin red. Validan conversión y parseo, no el modelo."""

from types import SimpleNamespace

import pytest
from google.genai import errors, types

from app.llm.anthropic import AnthropicLLM
from app.llm.base import LLMError, Message, ToolCall, ToolResult, ToolSpec
from app.llm.gemini import GeminiLLM

TOOLS = [ToolSpec("search_properties", "Busca", {"type": "object", "properties": {"zone": {"type": "string"}}})]


def gemini_response(parts, finish="STOP"):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=parts), finish_reason=finish)],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=100, candidates_token_count=20, thoughts_token_count=30, total_token_count=150))


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def generate_content(self, *, model, contents, config):
        self.requests.append({"model": model, "contents": contents, "config": config})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_gemini_parses_function_call_and_usage():
    raw_part = types.Part(function_call=types.FunctionCall(id="fc1", name="search_properties",
                                                           args={"zone": "Cholula"}), thought_signature=b"sig")
    models = FakeModels([gemini_response([types.Part(text="pensando", thought=True), raw_part])])
    llm = GeminiLLM(None, "gemini-3.8-flash", client=SimpleNamespace(models=models))
    resp = llm.generate(system="s", messages=[Message(role="user", text="hola")], tools=TOOLS, timeout_s=10)
    assert resp.message.text == ""  # el pensamiento no se muestra
    assert resp.message.tool_calls[0].name == "search_properties" and resp.message.tool_calls[0].provider_id == "fc1"
    assert (resp.usage.input_tokens, resp.usage.output_tokens, resp.usage.thinking_tokens) == (100, 20, 30)
    config = models.requests[0]["config"]
    assert config.automatic_function_calling.disable is True and config.http_options.timeout == 10_000


def test_gemini_replays_model_content_intact_with_thought_signature():
    llm = GeminiLLM(None, "gemini-3.8-flash", client=SimpleNamespace(models=FakeModels([])))
    raw = types.Content(role="model", parts=[types.Part(
        function_call=types.FunctionCall(id="fc1", name="search_properties", args={}), thought_signature=b"sig")])
    history = [
        Message(role="user", text="hola"),
        Message(role="assistant", tool_calls=[ToolCall("fc1", "search_properties", {}, "fc1")], provider="gemini",
                raw=raw),
        Message(role="tool", tool_results=[ToolResult("fc1", "search_properties", {"count": 0}, False, "fc1")]),
    ]
    contents = llm.to_contents(history)
    assert contents[1] is raw and contents[1].parts[0].thought_signature == b"sig"
    fr = contents[2].parts[0].function_response
    assert contents[2].role == "user" and fr.id == "fc1" and fr.response == {"output": {"count": 0}}


def test_gemini_blocked_response_is_empty():
    models = FakeModels([gemini_response([types.Part(text="x")], finish="SAFETY")])
    llm = GeminiLLM(None, "m", client=SimpleNamespace(models=models))
    resp = llm.generate(system="s", messages=[Message(role="user", text="x")], tools=TOOLS, timeout_s=5)
    assert resp.message.text == "" and resp.finish_reason == "SAFETY"


@pytest.mark.parametrize("code,kind,retryable", [(429, "rate_limited", True), (503, "server_error", True),
                                                 (403, "auth", False), (400, "bad_request", False)])
def test_gemini_error_mapping(code, kind, retryable):
    cls = errors.ServerError if code >= 500 else errors.ClientError
    models = FakeModels([cls(code, {"error": {"code": code, "message": "x", "status": "X"}})])
    llm = GeminiLLM(None, "m", client=SimpleNamespace(models=models))
    with pytest.raises(LLMError) as exc:
        llm.generate(system="s", messages=[Message(role="user", text="x")], tools=TOOLS, timeout_s=5)
    assert exc.value.kind == kind and exc.value.retryable is retryable


def test_gemini_not_configured_raises_friendly_error():
    with pytest.raises(LLMError) as exc:
        GeminiLLM(None, "m").generate(system="s", messages=[], tools=TOOLS, timeout_s=5)
    assert exc.value.kind == "not_configured"


def test_anthropic_adapter_conversion_and_parsing():
    """Pendiente de validación real: esto solo prueba el contrato con objetos del SDK."""
    from anthropic.types import Message as AMessage
    from anthropic.types import TextBlock, ToolUseBlock, Usage

    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return AMessage(id="msg_1", type="message", role="assistant", model="claude-sonnet-5-5",
                        content=[TextBlock(type="text", text="Busco."),
                                 ToolUseBlock(type="tool_use", id="tu_1", name="search_properties",
                                              input={"zone": "Cholula"})],
                        stop_reason="tool_use", stop_sequence=None,
                        usage=Usage(input_tokens=50, output_tokens=10))

    llm = AnthropicLLM(None, "claude-sonnet-5-5", client=SimpleNamespace(messages=SimpleNamespace(create=create)))
    history = [Message(role="user", text="hola"),
               Message(role="assistant", text="", tool_calls=[ToolCall("tu_0", "search_properties", {})]),
               Message(role="tool", tool_results=[ToolResult("tu_0", "search_properties", {"count": 0})]),
               Message(role="user", text="¿y en Cholula?")]
    resp = llm.generate(system="s", messages=history, tools=TOOLS, timeout_s=10)
    assert resp.message.tool_calls[0].id == "tu_1" and resp.usage.input_tokens == 50
    roles = [m["role"] for m in captured["messages"]]
    assert roles == ["user", "assistant", "user"]  # tool_result + texto del usuario fusionados
    assert captured["messages"][2]["content"][0]["type"] == "tool_result"
    assert AnthropicLLM.validated_against_real_api is False
