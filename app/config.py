"""Configuración leída del entorno. Ningún secreto tiene valor por defecto."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import timedelta, timezone

# Precios en USD por 1M de tokens (entrada, salida+thinking). Fuente: ai.google.dev/gemini-api/docs/pricing,
# consultada 2026-10-13. Solo sirven para *estimar*; la factura real la da Google.
PRICES_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.1-flash-lite": (0.25, 1.50),
}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw not in (None, "") else default
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        return float(raw) if raw not in (None, "") else default
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _str(name: str, default: str | None = None) -> str | None:
    raw = os.getenv(name)
    return raw.strip() if raw and raw.strip() else default


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "gemini"
    gemini_api_key: str | None = field(default=None, repr=False)
    gemini_model: str = "gemini-3.8-flash"
    gemini_thinking_level: str = "low"
    anthropic_api_key: str | None = field(default=None, repr=False)
    anthropic_model: str = "claude-sonnet-5-5"
    admin_token: str | None = field(default=None, repr=False)
    whatsapp_number: str | None = None
    db_path: str = "data/inmobot.db"
    catalog_path: str = "properties.json"
    max_message_chars: int = 1000
    max_history_turns: int = 12
    max_tool_rounds: int = 4
    turn_deadline_s: float = 20.0
    rate_limit_per_minute: int = 12
    rate_limit_per_hour: int = 120
    daily_token_budget: int = 1_000_000
    trust_proxy: bool = False
    session_ttl_s: int = 7200
    max_sessions: int = 2000
    allowed_origins: tuple[str, ...] = ()
    utc_offset_hours: int = -6  # Ciudad de México: UTC-6 fijo desde 2022 (sin horario de verano)

    @property
    def local_tz(self) -> timezone:
        return timezone(timedelta(hours=self.utc_offset_hours))

    @property
    def active_model(self) -> str:
        return self.anthropic_model if self.llm_provider == "anthropic" else self.gemini_model

    @classmethod
    def from_env(cls) -> Settings:
        origins = _str("ALLOWED_ORIGINS", "") or ""
        whatsapp = "".join(ch for ch in (_str("WHATSAPP_NUMBER", "") or "") if ch.isdigit()) or None
        return cls(
            llm_provider=(_str("LLM_PROVIDER", "gemini") or "gemini").lower(),
            gemini_api_key=_str("GEMINI_API_KEY") or _str("GOOGLE_API_KEY"),
            gemini_model=_str("GEMINI_MODEL", cls.gemini_model) or cls.gemini_model,
            gemini_thinking_level=(_str("GEMINI_THINKING_LEVEL", "low") or "low").lower(),
            anthropic_api_key=_str("ANTHROPIC_API_KEY"),
            anthropic_model=_str("ANTHROPIC_MODEL", cls.anthropic_model) or cls.anthropic_model,
            admin_token=_str("ADMIN_TOKEN"),
            whatsapp_number=whatsapp,
            db_path=_str("DB_PATH", cls.db_path) or cls.db_path,
            catalog_path=_str("CATALOG_PATH", cls.catalog_path) or cls.catalog_path,
            max_message_chars=_int("MAX_MESSAGE_CHARS", cls.max_message_chars),
            max_history_turns=_int("MAX_HISTORY_TURNS", cls.max_history_turns),
            max_tool_rounds=_int("MAX_TOOL_ROUNDS", cls.max_tool_rounds),
            turn_deadline_s=_float("TURN_DEADLINE_S", cls.turn_deadline_s),
            rate_limit_per_minute=_int("RATE_LIMIT_PER_MINUTE", cls.rate_limit_per_minute),
            rate_limit_per_hour=_int("RATE_LIMIT_PER_HOUR", cls.rate_limit_per_hour),
            daily_token_budget=_int("DAILY_TOKEN_BUDGET", cls.daily_token_budget),
            trust_proxy=_bool("TRUST_PROXY", False),
            session_ttl_s=_int("SESSION_TTL_S", cls.session_ttl_s),
            max_sessions=_int("MAX_SESSIONS", cls.max_sessions),
            allowed_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        )


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    price = PRICES_USD_PER_MTOK.get(model)
    if price is None:
        return None
    return round(input_tokens * price[0] / 1_000_000 + output_tokens * price[1] / 1_000_000, 6)
