"""Regresiones de la revisión independiente del PR #2 (H1, H2, H3, H6) y huecos de cobertura señalados."""

import re
from datetime import timezone
from pathlib import Path
from types import SimpleNamespace

from app.agent import Agent
from app.config import _thinking_level
from app.guards import TokenBudget, UsageTracker, client_ip
from app.llm import fake
from app.llm.base import LLMResponse, Message, ToolCall, Usage
from app.llm.fake import FakeLLM
from app.llm.gemini import GeminiLLM
from app.prompts import build_system_prompt
from app.sessions import Session, trim_history
from app.tools import ToolExecutor, build_tool_specs


def make_agent(catalog, leads, script):
    return Agent(FakeLLM(script), ToolExecutor(catalog, leads, None), build_system_prompt(catalog.zones),
                 build_tool_specs(catalog), budget=TokenBudget(10**9, timezone.utc), usage=UsageTracker(),
                 sleep=lambda s: None)


def test_h1_every_function_call_gets_a_response(catalog, leads):
    calls = [ToolCall(id=f"c{i}", name="get_property", args={"property_id": 4}) for i in range(7)]
    many = LLMResponse(Message(role="assistant", tool_calls=calls, provider="fake"), Usage(1, 1))
    agent = make_agent(catalog, leads, [many, fake.text("ok")])
    session = Session(id="s1")
    agent.run_turn(session, "detalles")
    tool_msg = next(m for m in session.history if m.role == "tool")
    assert [r.call_id for r in tool_msg.tool_results] == [c.id for c in calls]
    assert sum(r.is_error for r in tool_msg.tool_results) == 2


def test_h2_tool_crash_returns_error_and_history_stays_valid(catalog, leads):
    agent = make_agent(catalog, leads, [fake.tool("save_lead", {"name": "Ana", "max_budget_mxn": 1e30}),
                                        fake.text("No pude guardar eso.")])
    session = Session(id="s1")
    result = agent.run_turn(session, "mi presupuesto es infinito")
    assert result.reply == "No pude guardar eso."
    assert [m.role for m in session.history] == ["user", "assistant", "tool", "assistant"]
    assert session.history[2].tool_results[0].is_error


def test_h2_unexpected_tool_exception_is_contained(catalog, leads):
    executor = ToolExecutor(catalog, leads, None)
    executor._t_get_property = lambda args, sid: (_ for _ in ()).throw(RuntimeError("boom"))
    out = executor.execute(ToolCall(id="c1", name="get_property", args={"property_id": 4}), "s1")
    assert out.is_error and "interno" in out.content["error"]


def test_h3_gemini_disables_automatic_continuation():
    llm = GeminiLLM(None, "gemini-3.8-flash", client=SimpleNamespace(models=None))
    config = llm.build_config("s", build_tool_specs_stub(), 10, "auto")
    assert config.automatic_continuation is False


def build_tool_specs_stub():
    from app.llm.base import ToolSpec
    return [ToolSpec("t", "d", {"type": "object", "properties": {}})]


def test_h6_invalid_thinking_level_falls_back_to_low():
    assert _thinking_level("ultra") == "low" and _thinking_level("MEDIUM") == "medium"


def test_client_ip_uses_last_forwarded_hop_only_when_trusted():
    request = SimpleNamespace(headers={"x-forwarded-for": "6.6.6.6, 203.0.113.9"},
                              client=SimpleNamespace(host="10.0.0.1"))
    assert client_ip(request, trust_proxy=True) == "203.0.113.9"
    assert client_ip(request, trust_proxy=False) == "10.0.0.1"


def test_trim_history_starts_on_a_user_message():
    history = []
    for i in range(20):
        history += [Message(role="user", text=f"u{i}"), Message(role="assistant", text=f"a{i}")]
    trimmed = trim_history(history, 12)
    assert trimmed[0].role == "user" and trimmed[0].text == "u8" and len(trimmed) == 24


def test_static_ui_never_uses_innerhtml():
    for path in Path("static").glob("*"):
        assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", path.read_text()), path
