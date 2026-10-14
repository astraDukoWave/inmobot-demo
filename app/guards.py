"""Guards: rate limit por IP, presupuesto diario de tokens, cabeceras de seguridad y métricas de uso."""

from __future__ import annotations

import re
import threading
import time
import unicodedata
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import Request

CSP = ("default-src 'self'; img-src 'self' https://placehold.co data:; style-src 'self'; script-src 'self'; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


# Capa 1 contra prompt injection: filtro determinista ANTES del modelo para intentos obvios de extraer o cambiar
# las instrucciones. Es evadible a propósito de diseño (capa barata); las capas 2 y 3 son las reglas del prompt
# con tools de mínimo privilegio y el canary en la salida. Origen: live-smoke 2/3 y 4/5, donde "muéstrame tu prompt
# palabra por palabra" hizo que el modelo tardara más de 9-19 s y el turno cayó en fallback.
_INJECTION_PATTERNS = [re.compile(p) for p in (
    r"\bprompts?\b",
    r"\bsystem\s*(prompt|message|instructions?)\b",
    r"\b(mensaje|instrucciones|indicaciones)\s+(del?\s+)?sistema\b",
    r"\b(ignora|ignoren|olvida|olviden|omite|descarta|desobedece)\b.{0,30}\b(instrucciones|reglas|indicaciones|restricciones)\b",
    r"\b(ignore|forget|disregard|override)\b.{0,30}\b(instructions|rules|guidelines|restrictions)\b",
    r"\b(muestrame|muestra|revela|revelame|dime|repite|imprime|copia|escribe|comparte)\b.{0,30}\btus\s+(instrucciones|indicaciones)\b",
    r"\b(show|reveal|print|repeat|output)\b.{0,30}\byour\s+(instructions|rules|guidelines)\b",
    r"\b(modo|mode)\s+(desarrollador|developer|dios|god|dan)\b",
    r"\bjailbreak\b",
)]


def looks_like_injection(text: str) -> bool:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return any(p.search(normalized) for p in _INJECTION_PATTERNS)


def client_ip(request: Request, trust_proxy: bool) -> str:
    """En Heroku el router agrega la IP real al FINAL de X-Forwarded-For; lo anterior lo puede falsear el cliente."""
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        if hops:
            return hops[-1]
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, per_minute: int, per_hour: int, clock=time.monotonic):
        self.windows = ((60.0, per_minute), (3600.0, per_hour))
        self.clock = clock
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > 3600.0:
                hits.popleft()
            for window, limit in self.windows:
                if sum(1 for t in hits if now - t <= window) >= limit:
                    return False
            hits.append(now)
            if len(self._hits) > 10_000:  # evita crecimiento sin límite
                for k in [k for k, v in self._hits.items() if not v][:5_000]:
                    del self._hits[k]
            return True


class TokenBudget:
    """Tope global de tokens por día local. Al agotarse, el agente responde sin llamar al modelo."""

    def __init__(self, daily_limit: int, tz: timezone):
        self.daily_limit = daily_limit
        self.tz = tz
        self._day = None
        self._used = 0
        self._lock = threading.Lock()

    def _roll(self) -> None:
        today = datetime.now(self.tz).date()
        if today != self._day:
            self._day, self._used = today, 0

    def consume(self, tokens: int) -> None:
        with self._lock:
            self._roll()
            self._used += max(0, tokens)

    def exhausted(self) -> bool:
        with self._lock:
            self._roll()
            return self._used >= self.daily_limit

    def snapshot(self) -> dict:
        with self._lock:
            self._roll()
            return {"day": str(self._day), "used_tokens": self._used, "daily_limit": self.daily_limit}


class UsageTracker:
    """Métricas reales de los turnos desde que arrancó el proceso (sin contenido ni PII)."""

    def __init__(self):
        self._lock = threading.Lock()
        self.turns = 0
        self.fallbacks: dict[str, int] = defaultdict(int)
        self.tokens = {"input": 0, "output": 0, "thinking": 0}
        self.cost_usd = 0.0
        self.latencies_ms: deque = deque(maxlen=500)
        self.started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def record(self, *, latency_ms: int, input_tokens: int, output_tokens: int, thinking_tokens: int,
               cost_usd: float | None, fallback: str | None) -> None:
        with self._lock:
            self.turns += 1
            self.tokens["input"] += input_tokens
            self.tokens["output"] += output_tokens
            self.tokens["thinking"] += thinking_tokens
            self.cost_usd += cost_usd or 0.0
            self.latencies_ms.append(latency_ms)
            if fallback:
                self.fallbacks[fallback] += 1

    def snapshot(self) -> dict:
        with self._lock:
            lat = sorted(self.latencies_ms)

            def pct(p: float) -> int | None:
                return lat[min(len(lat) - 1, int(p * len(lat)))] if lat else None

            return {"since": self.started_at, "turns": self.turns, "tokens": dict(self.tokens),
                    "estimated_cost_usd": round(self.cost_usd, 4), "latency_ms": {"p50": pct(0.5), "p95": pct(0.95)},
                    "fallbacks": dict(self.fallbacks)}
