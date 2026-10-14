"""Bucle del agente: generate → tools → generate, con deadline total por turno (A5) y grounding de tarjetas."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field

from .config import estimate_cost_usd
from .guards import TokenBudget, UsageTracker, looks_like_injection
from .llm.base import LLMClient, LLMError, Message, ToolResult, ToolSpec, Usage
from .prompts import CANARY
from .sessions import Session
from .tools import ToolExecutor

log = logging.getLogger("inmobot.agent")

MSG_PROVIDER = ("Perdón, en este momento no puedo responder: el servicio de IA no está disponible. "
                "Si quieres, continúa con un asesor por WhatsApp.")
MSG_BUDGET = "La demo alcanzó su límite de uso de hoy. Si quieres, continúa con un asesor por WhatsApp."
MSG_EMPTY = "Perdón, no te entendí bien. ¿Me lo dices de otra forma?"
MSG_LEAK = ("No puedo compartir mis instrucciones internas, pero con gusto te ayudo a encontrar propiedad en "
            "Puebla. ¿Qué zona te interesa?")
MSG_DONE = "Listo. ¿Te ayudo con algo más?"
MSG_GUARD = ("No puedo compartir ni cambiar mis instrucciones, pero con gusto te ayudo a encontrar propiedad en "
             "Puebla. ¿Qué zona te interesa?")
MAX_CALLS_PER_ROUND = 5
MIN_CALL_BUDGET_S = 2.0
FIRST_ATTEMPT_CAP_S = 9.0
RETRY_EMPTY = {"MALFORMED_FUNCTION_CALL", "UNEXPECTED_TOOL_CALL", "OTHER", "EMPTY"}


@dataclass
class TurnResult:
    reply: str
    cards: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    lead_saved: bool = False
    usage: Usage = field(default_factory=Usage)
    tool_calls: list[str] = field(default_factory=list)
    rounds: int = 0
    latency_ms: int = 0
    fallback: str | None = None
    errors: list[str] = field(default_factory=list)  # errores del proveedor (tipo y código, sin contenido)
    guard: str | None = None  # capa que respondió sin llamar al modelo (comportamiento esperado, no degradación)


class Agent:
    def __init__(self, llm: LLMClient, executor: ToolExecutor, system_prompt: str, tools: list[ToolSpec], *,
                 budget: TokenBudget, usage: UsageTracker, max_rounds: int = 4, deadline_s: float = 20.0,
                 clock=time.monotonic, sleep=time.sleep):
        self.llm = llm
        self.executor = executor
        self.system_prompt = system_prompt
        self.tools = tools
        self.budget = budget
        self.usage = usage
        self.max_rounds = max_rounds
        self.deadline_s = deadline_s
        self.clock = clock
        self.sleep = sleep

    def _generate(self, history: list[Message], deadline: float, errors: list[str], tool_choice: str = "auto"):
        """Una llamada con tope de tiempo; si falla de forma reintentable, un reintento con lo que quede del turno.

        El primer intento se limita a FIRST_ATTEMPT_CAP_S para que una llamada colgada no consuma todo el turno
        (live-smoke 2/3: una sola llamada se llevó 19.2 s y no quedó margen para reintentar).
        """
        last = LLMError("unreachable")
        for attempt in (1, 2):
            remaining = deadline - self.clock()
            if remaining < MIN_CALL_BUDGET_S:
                raise LLMError("deadline", "sin tiempo para llamar al modelo")
            timeout = remaining - 0.5
            if attempt == 1:
                timeout = min(timeout, FIRST_ATTEMPT_CAP_S)
            started = self.clock()
            try:
                return self.llm.generate(system=self.system_prompt, messages=history, tools=self.tools,
                                         timeout_s=timeout, tool_choice=tool_choice)
            except LLMError as exc:
                last = exc
                errors.append(f"{exc} @{int((self.clock() - started) * 1000)}ms")
                if attempt == 2 or not exc.retryable or deadline - self.clock() < MIN_CALL_BUDGET_S + 1.5:
                    raise
                self.sleep(0.5)
            except Exception as exc:  # cualquier sorpresa del SDK se trata como fallo del proveedor
                errors.append(f"unexpected: {type(exc).__name__}")
                raise LLMError("unexpected", type(exc).__name__) from exc
        raise last

    def run_turn(self, session: Session, user_text: str) -> TurnResult:
        start = self.clock()
        deadline = start + self.deadline_s
        session.history.append(Message(role="user", text=user_text))
        session.turns += 1
        result = TurnResult(reply="")
        cards: list[dict] | None = None
        actions: dict[str, dict] = {}

        if looks_like_injection(user_text):
            result.guard = "injection"
            return self._finish(session, result, start, MSG_GUARD, None, cards, actions)

        if self.budget.exhausted():
            return self._finish(session, result, start, MSG_BUDGET, "budget", cards, actions, offer_whatsapp=True)

        reply = ""
        retried_empty = False
        for round_no in range(1, self.max_rounds + 1):
            result.rounds = round_no
            try:
                response = self._generate(session.history, deadline, result.errors)
            except LLMError as exc:
                return self._finish(session, result, start, MSG_PROVIDER, exc.kind, cards, actions,
                                    offer_whatsapp=True)
            result.usage = result.usage + response.usage
            self.budget.consume(response.usage.total)
            message = response.message
            if not message.text and not message.tool_calls:
                if not retried_empty and response.finish_reason in RETRY_EMPTY:
                    retried_empty = True  # p. ej. MALFORMED_FUNCTION_CALL: un intento más si queda tiempo
                    continue
                return self._finish(session, result, start, MSG_EMPTY, f"empty:{response.finish_reason}",
                                    cards, actions)
            session.history.append(message)
            if not message.tool_calls:
                reply = message.text
                break
            tool_results = []
            for index, call in enumerate(message.tool_calls):
                if index >= MAX_CALLS_PER_ROUND:
                    # Cada function_call necesita su respuesta o el proveedor rechaza el historial (hallazgo H1).
                    tool_results.append(ToolResult(call_id=call.id, name=call.name, is_error=True,
                                                   content={"error": "Límite de llamadas por ronda; no se ejecutó."},
                                                   provider_id=call.provider_id))
                    continue
                outcome = self.executor.execute(call, session.id)
                result.tool_calls.append(call.name)
                if outcome.cards is not None:
                    cards = outcome.cards  # grounding: solo resultados de tools; gana la última del turno
                for action in outcome.actions:
                    actions[action["type"]] = action
                result.lead_saved = result.lead_saved or outcome.lead_saved
                tool_results.append(ToolResult(call_id=call.id, name=call.name, content=outcome.content,
                                               is_error=outcome.is_error, provider_id=call.provider_id))
            session.history.append(Message(role="tool", tool_results=tool_results))
        else:
            # Se acabaron las rondas: una última llamada sin tools para cerrar con texto.
            try:
                response = self._generate(session.history, deadline, result.errors, tool_choice="none")
                result.usage = result.usage + response.usage
                self.budget.consume(response.usage.total)
                if response.message.text and not response.message.tool_calls:
                    session.history.append(response.message)
                    reply = response.message.text
            except LLMError:
                pass
            if not reply:
                return self._finish(session, result, start, MSG_DONE, "max_rounds", cards, actions)

        if CANARY in reply:
            session.history[-1] = Message(role="assistant", text=MSG_LEAK)
            return self._finish(session, result, start, None, "canary", cards, actions, keep_history=True,
                                reply_override=MSG_LEAK)
        return self._finish(session, result, start, None, None, cards, actions, keep_history=True,
                            reply_override=reply)

    def _finish(self, session: Session, result: TurnResult, start: float, fallback_text: str | None,
                fallback_kind: str | None, cards, actions: dict, offer_whatsapp: bool = False,
                keep_history: bool = False, reply_override: str | None = None) -> TurnResult:
        if fallback_text is not None and not keep_history:
            # Mantiene la alternancia user/assistant para cualquier proveedor.
            session.history.append(Message(role="assistant", text=fallback_text))
        if offer_whatsapp and self.executor.whatsapp_number and "whatsapp" not in actions:
            actions["whatsapp"] = self.executor.whatsapp_action(session.id)
        result.reply = reply_override if reply_override is not None else (fallback_text or "")
        result.cards = cards or []
        result.actions = list(actions.values())
        result.fallback = fallback_kind
        result.latency_ms = int((self.clock() - start) * 1000)
        cost = estimate_cost_usd(self.llm.model, result.usage.input_tokens,
                                 result.usage.output_tokens + result.usage.thinking_tokens)
        self.usage.record(latency_ms=result.latency_ms, input_tokens=result.usage.input_tokens,
                          output_tokens=result.usage.output_tokens, thinking_tokens=result.usage.thinking_tokens,
                          cost_usd=cost, fallback=fallback_kind)
        log.info(json.dumps({
            "event": "turn", "session": hashlib.sha256(session.id.encode()).hexdigest()[:10],
            "turn": session.turns, "provider": self.llm.provider, "model": self.llm.model,
            "latency_ms": result.latency_ms, "rounds": result.rounds, "tools": result.tool_calls,
            "tokens_in": result.usage.input_tokens, "tokens_out": result.usage.output_tokens,
            "tokens_thinking": result.usage.thinking_tokens, "cost_usd_est": cost,
            "cards": [c["id"] for c in result.cards], "fallback": fallback_kind, "errors": result.errors,
            "guard": result.guard,
        }))
        return result
