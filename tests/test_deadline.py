"""Regresiones de A5 / REQ-19: el turno completo no pasa de su límite, ni con llamadas colgadas ni con respuestas
tardías, y ninguna tool empieza cuando ya no alcanza el tiempo. Varias usan reloj real con un límite de 1 s."""

import time
from datetime import timezone

from fastapi.testclient import TestClient

from app.agent import MSG_PROVIDER, Agent
from app.config import Settings
from app.guards import TokenBudget, UsageTracker
from app.leads import LeadStore
from app.llm import fake
from app.llm.fake import FakeLLM
from app.main import create_app
from app.prompts import build_system_prompt
from app.sessions import Session
from app.tools import ToolExecutor, build_tool_specs

LEAD_AND_VISIT = [("save_lead", {"name": "Ana Prueba", "phone": "2221234567"}),
                  ("request_visit", {"property_id": 4, "preferred_date": "sábado"})]


def hang(seconds=1.5, reply="respuesta tardía"):
    def step(messages):
        time.sleep(seconds)
        return fake.text(reply)
    return step


def agent_for(catalog, leads, script, deadline_s=20.0, clock=None):
    kwargs = {"clock": clock} if clock else {}
    return Agent(FakeLLM(script), ToolExecutor(catalog, leads, None), build_system_prompt(catalog.zones),
                 build_tool_specs(catalog), budget=TokenBudget(10**9, timezone.utc), usage=UsageTracker(),
                 deadline_s=deadline_s, **kwargs)


def tool_calls_response(calls):
    from app.llm.base import LLMResponse, Message, ToolCall, Usage
    tc = [ToolCall(id=f"c{i}", name=name, args=args) for i, (name, args) in enumerate(calls)]
    return LLMResponse(Message(role="assistant", tool_calls=tc, provider="fake"), Usage(1, 1))


def test_hung_call_cannot_exceed_turn_budget(catalog, leads):
    """Reloj real: las dos llamadas se cuelgan 1.5 s y el turno de 1 s responde a tiempo."""
    agent = agent_for(catalog, leads, [hang(), hang()], deadline_s=1.0)
    session = Session(id="s1")
    started = time.monotonic()
    result = agent.run_turn(session, "hola")
    elapsed = time.monotonic() - started
    assert elapsed <= 1.15, elapsed
    assert result.reply == MSG_PROVIDER and result.fallback == "timeout"
    assert len(result.errors) == 2 and all(e.startswith("timeout") for e in result.errors)
    assert [m.role for m in session.history] == ["user", "assistant"]
    assert all("tardía" not in (m.text or "") for m in session.history)


def test_late_response_with_tool_calls_starts_no_tool(catalog, leads):
    now = [0.0]

    def late(messages):
        now[0] = 19.5  # llega con 0.5 s restantes: no alcanza para tools + cierre
        return tool_calls_response(LEAD_AND_VISIT)

    agent = agent_for(catalog, leads, [late], clock=lambda: now[0])
    session = Session(id="s1")
    result = agent.run_turn(session, "Soy Ana, 2221234567, quiero visitar Los Fresnos")
    assert result.fallback == "late_response" and result.tool_calls == []
    assert leads.get_by_session("s1") is None and leads.list_leads() == []
    assert [m.role for m in session.history] == ["user", "assistant"]


def test_text_arriving_after_deadline_is_discarded(catalog, leads):
    now = [0.0]

    def after(messages):
        now[0] = 20.5
        return fake.text("demasiado tarde")

    agent = agent_for(catalog, leads, [after], clock=lambda: now[0])
    result = agent.run_turn(Session(id="s1"), "hola")
    assert result.fallback == "late_response" and result.reply == MSG_PROVIDER


def test_no_tool_starts_once_the_deadline_passes_mid_round(catalog, leads):
    now = [0.0]
    agent = agent_for(catalog, leads, [tool_calls_response(LEAD_AND_VISIT)], clock=lambda: now[0])
    real_execute = agent.executor.execute

    def slow_execute(call, session_id):
        outcome = real_execute(call, session_id)
        now[0] = 20.5  # la primera tool termina después del límite
        return outcome

    agent.executor.execute = slow_execute
    session = Session(id="s1")
    result = agent.run_turn(session, "Soy Ana, 2221234567, quiero visitar Los Fresnos")
    assert result.tool_calls == ["save_lead"] and result.fallback == "deadline"
    assert leads.list_leads()[0]["visits"] == []  # request_visit nunca empezó
    tool_msg = session.history[2]
    assert [r.name for r in tool_msg.tool_results] == ["save_lead", "request_visit"]
    assert tool_msg.tool_results[1].is_error and "tiempo" in tool_msg.tool_results[1].content["error"]
    assert [m.role for m in session.history] == ["user", "assistant", "tool", "assistant"]


def _client(tmp_path, catalog, script, **overrides):
    settings = Settings(llm_provider="fake", admin_token="t", db_path=str(tmp_path / "d.db"), **overrides)
    app = create_app(settings=settings, llm=FakeLLM(script), catalog=catalog, leads=LeadStore(settings.db_path))
    return TestClient(app, raise_server_exceptions=False)


def test_api_turn_with_hung_provider_answers_in_budget_and_releases_the_lock(tmp_path, catalog):
    client = _client(tmp_path, catalog, [hang(), hang(), fake.text("¡Hola de nuevo!")], turn_deadline_s=1.0)
    started = time.monotonic()
    first = client.post("/api/chat", json={"message": "hola"})
    elapsed = time.monotonic() - started
    assert first.status_code == 200 and first.json()["reply"] == MSG_PROVIDER and elapsed <= 1.3, elapsed
    second = client.post("/api/chat", json={"session_id": first.json()["session_id"], "message": "¿sigues?"})
    assert second.status_code == 200 and second.json()["reply"] == "¡Hola de nuevo!"  # no 409: candado libre


def test_session_lock_is_released_when_the_turn_crashes(tmp_path, catalog):
    client = _client(tmp_path, catalog, [fake.text("uno"), fake.text("tres")])
    sid = client.post("/api/chat", json={"message": "hola"}).json()["session_id"]
    agent = client.app.state.agent
    original = agent.run_turn
    agent.run_turn = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    assert client.post("/api/chat", json={"session_id": sid, "message": "dos"}).status_code == 500
    agent.run_turn = original
    third = client.post("/api/chat", json={"session_id": sid, "message": "tres"})
    assert third.status_code == 200 and third.json()["reply"] == "tres"


def test_logs_carry_no_user_text_name_or_phone(tmp_path, catalog, caplog):
    client = _client(tmp_path, catalog, [fake.tool("save_lead", {"name": "Ana Prueba", "phone": "2221234567"}),
                                         fake.text("Gracias, Ana.")])
    with caplog.at_level("INFO"):
        client.post("/api/chat", json={"message": "Me llamo Ana Prueba, mi teléfono es 2221234567"})
    text = " ".join(r.getMessage() for r in caplog.records)
    assert '"event": "turn"' in text
    for secret in ("Ana Prueba", "2221234567", "Me llamo", "Gracias"):
        assert secret not in text


def test_admin_usage_requires_token(tmp_path, catalog):
    client = _client(tmp_path, catalog, [])
    assert client.get("/api/admin/usage").status_code == 401
    body = client.get("/api/admin/usage", headers={"Authorization": "Bearer t"}).json()
    assert "budget" in body and "turns" in body
