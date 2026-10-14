"""Sesiones en memoria con UUID4 del servidor, TTL, tope LRU e historial acotado (un solo proceso: trigger T1)."""

from __future__ import annotations

import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

from .llm.base import Message


@dataclass
class Session:
    id: str
    history: list[Message] = field(default_factory=list)
    last_seen: float = field(default_factory=time.monotonic)
    lock: threading.Lock = field(default_factory=threading.Lock)
    turns: int = 0


def _valid_uuid(value: str | None) -> bool:
    if not value:
        return False
    try:
        return str(uuid.UUID(value, version=4)) == value
    except (ValueError, AttributeError, TypeError):
        return False


class SessionStore:
    def __init__(self, ttl_s: int, max_sessions: int):
        self.ttl_s = ttl_s
        self.max_sessions = max_sessions
        self._items: OrderedDict[str, Session] = OrderedDict()
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str | None) -> tuple[Session, bool]:
        now = time.monotonic()
        with self._lock:
            for sid in [s for s, sess in self._items.items() if now - sess.last_seen > self.ttl_s]:
                del self._items[sid]
            if _valid_uuid(session_id) and session_id in self._items:
                session = self._items[session_id]
                session.last_seen = now
                self._items.move_to_end(session_id)
                return session, False
            session = Session(id=str(uuid.uuid4()))
            self._items[session.id] = session
            while len(self._items) > self.max_sessions:
                self._items.popitem(last=False)
            return session, True

    def __len__(self) -> int:
        return len(self._items)


def trim_history(history: list[Message], max_turns: int) -> list[Message]:
    """Conserva los últimos `max_turns` turnos completos; corta solo antes de un mensaje del usuario."""
    user_idx = [i for i, m in enumerate(history) if m.role == "user"]
    if len(user_idx) <= max_turns:
        return history
    return history[user_idx[-max_turns]:]
