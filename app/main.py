"""API HTTP de InmoBot. Arranque: uvicorn app.main:create_app --factory"""

from __future__ import annotations

import hmac
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .agent import Agent
from .catalog import AmbiguousAmountError, Catalog
from .config import Settings
from .guards import CSP, SECURITY_HEADERS, RateLimiter, TokenBudget, UsageTracker, client_ip
from .leads import SCORES, LeadStore, since_from_label
from .llm import LLMClient, build_llm
from .prompts import PROMPT_VERSION, build_system_prompt
from .sessions import SessionStore, trim_history
from .tools import ToolExecutor, build_tool_specs

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
log = logging.getLogger("inmobot")


class ChatIn(BaseModel):
    session_id: str | None = None
    message: str = ""


class ChatOut(BaseModel):
    session_id: str
    reply: str
    cards: list[dict] = []
    actions: list[dict] = []
    lead_saved: bool = False


def _error(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "detail": detail})


def create_app(settings: Settings | None = None, llm: LLMClient | None = None, catalog: Catalog | None = None,
               leads: LeadStore | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = settings or Settings.from_env()
    catalog = catalog or Catalog.load(settings.catalog_path)
    leads = leads or LeadStore(settings.db_path)
    llm = llm or build_llm(settings)
    executor = ToolExecutor(catalog, leads, settings.whatsapp_number)
    budget = TokenBudget(settings.daily_token_budget, settings.local_tz)
    usage = UsageTracker()
    agent = Agent(llm, executor, build_system_prompt(catalog.zones), build_tool_specs(catalog), budget=budget,
                  usage=usage, max_rounds=settings.max_tool_rounds, deadline_s=settings.turn_deadline_s)
    sessions = SessionStore(settings.session_ttl_s, settings.max_sessions)
    limiter = RateLimiter(settings.rate_limit_per_minute, settings.rate_limit_per_hour)

    app = FastAPI(title="InmoBot API", version=__version__,
                  description="Agente inmobiliario de demostración (catálogo ficticio).")
    app.state.settings, app.state.agent, app.state.sessions = settings, agent, sessions
    app.state.leads, app.state.llm, app.state.budget, app.state.usage = leads, llm, budget, usage

    if settings.allowed_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins),
                           allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        if not request.url.path.startswith(("/docs", "/redoc", "/openapi")):
            response.headers.setdefault("Content-Security-Policy", CSP)
        return response

    def require_admin(authorization: str = Header(default="")) -> None:
        if not settings.admin_token:
            raise HTTPException(status_code=503, detail="admin deshabilitado: falta ADMIN_TOKEN")
        if not hmac.compare_digest(authorization.encode(), f"Bearer {settings.admin_token}".encode()):
            raise HTTPException(status_code=401, detail="token inválido")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__, "provider": llm.provider, "model": llm.model,
                "llm_configured": bool(getattr(llm, "configured", False)), "prompt_version": PROMPT_VERSION}

    @app.post("/api/chat", response_model=ChatOut)
    def chat(body: ChatIn, request: Request):
        text = " ".join((body.message or "").replace("\x00", "").split()) if body.message else ""
        if not text:
            return _error(422, "empty_message", "Escribe un mensaje.")
        if len(body.message) > settings.max_message_chars:
            return _error(422, "message_too_long", f"Tu mensaje es muy largo (máximo {settings.max_message_chars} "
                                                   "caracteres).")
        if not limiter.allow(client_ip(request, settings.trust_proxy)):
            log.info('{"event": "rate_limited"}')
            return _error(429, "rate_limited", "Vas muy rápido; intenta de nuevo en un momento.")
        session, _created = sessions.get_or_create(body.session_id)
        if not session.lock.acquire(blocking=False):
            return _error(409, "busy", "Espera la respuesta anterior.")
        try:
            result = agent.run_turn(session, text)
            session.history = trim_history(session.history, settings.max_history_turns)
        finally:
            session.lock.release()
        return ChatOut(session_id=session.id, reply=result.reply, cards=result.cards, actions=result.actions,
                       lead_saved=result.lead_saved)

    @app.get("/api/properties")
    def properties(zone: str | None = None, max_price_mxn: int | None = None, min_bedrooms: int | None = None,
                   property_type: str | None = None):
        normalized = catalog.normalize_zone(zone)
        if zone and not normalized:
            return _error(422, "unknown_zone", f"Zonas disponibles: {', '.join(catalog.zones)}")
        try:
            result = catalog.search(normalized, max_price_mxn, None, min_bedrooms, property_type)
        except AmbiguousAmountError:
            return _error(422, "ambiguous_amount", "Usa el monto completo en pesos (ej. 2500000).")
        return {"count": len(result.matches), "properties": [p.card() for p in result.matches],
                "alternatives": [p.card(alternative=True) for p in result.alternatives],
                "relaxed_criteria": result.relaxed, "zones": catalog.zones}

    @app.get("/api/admin/leads", dependencies=[Depends(require_admin)])
    def admin_leads(since: str = Query("all", pattern="^(today|7d|all)$"), score: str | None = None,
                    limit: int = Query(50, ge=1, le=500)):
        if score is not None and score not in SCORES:
            return _error(422, "bad_score", f"score debe ser uno de {SCORES}")
        return {"since": since, "leads": leads.list_leads(since_from_label(since, settings.local_tz), score, limit)}

    @app.get("/api/admin/stats", dependencies=[Depends(require_admin)])
    def admin_stats(since: str = Query("today", pattern="^(today|7d|all)$")):
        return {"since": since, "timezone": f"UTC{settings.utc_offset_hours:+d}",
                **leads.stats(since_from_label(since, settings.local_tz))}

    @app.get("/api/admin/usage", dependencies=[Depends(require_admin)])
    def admin_usage():
        return {"provider": llm.provider, "model": llm.model, "budget": budget.snapshot(), **usage.snapshot()}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
