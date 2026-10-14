"""Leads y solicitudes de visita en SQLite. Puntaje determinista y explicable (lo calcula el código, no el LLM).

SQLite vive en el disco efímero del dyno: solo para la demo con datos de prueba (A8).
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

PAYMENT_METHODS = ("credito_bancario", "infonavit_fovissste", "contado", "otro")
TIMELINES = ("inmediato", "1_3_meses", "3_6_meses", "mas_6_meses", "explorando")
SCORES = ("caliente", "tibio", "frio")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    name TEXT, phone TEXT, zone TEXT, max_budget_mxn INTEGER, bedrooms INTEGER, property_type TEXT,
    payment_method TEXT, timeline TEXT, interested_property_ids TEXT NOT NULL DEFAULT '[]',
    score TEXT NOT NULL, score_points INTEGER NOT NULL, score_reasons TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS visits (
    id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL REFERENCES leads(id),
    property_id INTEGER NOT NULL, property_name TEXT, preferred_date TEXT,
    status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
"""

LEAD_FIELDS = ("name", "phone", "zone", "max_budget_mxn", "bedrooms", "property_type", "payment_method", "timeline")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_mx_phone(raw: str | None) -> str | None:
    """10 dígitos de México, con o sin +52 / +521. Devuelve +52XXXXXXXXXX o None si no es válido."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 13 and digits.startswith("521"):
        digits = digits[3:]
    elif len(digits) == 12 and digits.startswith("52"):
        digits = digits[2:]
    if len(digits) != 10 or digits[0] == "0":
        return None
    return "+52" + digits


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    return f"+52 ••• ••• {phone[-4:]}"


def score_lead(lead: dict, visit_requested: bool) -> tuple[str, int, list[str]]:
    points, reasons = 0, []
    if lead.get("phone"):
        points += 2
        reasons.append("contacto (+2)")
    if lead.get("max_budget_mxn"):
        points += 1
        reasons.append("presupuesto (+1)")
    if lead.get("zone"):
        points += 1
        reasons.append("zona (+1)")
    if lead.get("payment_method"):
        points += 1
        reasons.append("forma de pago (+1)")
    timeline = lead.get("timeline")
    if timeline in ("inmediato", "1_3_meses"):
        points += 2
        reasons.append("plazo ≤ 3 meses (+2)")
    elif timeline == "3_6_meses":
        points += 1
        reasons.append("plazo 3-6 meses (+1)")
    if visit_requested:
        points += 2
        reasons.append("pidió visita (+2)")
    if not lead.get("phone"):
        label = "frio"
    elif points >= 7:
        label = "caliente"
    elif points >= 4:
        label = "tibio"
    else:
        label = "frio"
    return label, points, reasons


class LeadStore:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # Una conexión compartida protegida con candado: un solo proceso (ver spec, trigger T1).
        self._conn = sqlite3.connect(path, check_same_thread=False, timeout=5)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        for key in ("interested_property_ids", "score_reasons"):
            if key in d and isinstance(d[key], str):
                d[key] = json.loads(d[key])
        return d

    def get_by_session(self, session_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM leads WHERE session_id = ?", (session_id,)).fetchone()
        return self._row(row)

    def _has_visit(self, lead_id: str) -> bool:
        return self._conn.execute("SELECT 1 FROM visits WHERE lead_id = ? LIMIT 1", (lead_id,)).fetchone() is not None

    def upsert_lead(self, session_id: str, fields: dict, interested_ids: list[int] | None = None) -> dict:
        now = iso(utcnow())
        with self._lock:
            row = self._conn.execute("SELECT * FROM leads WHERE session_id = ?", (session_id,)).fetchone()
            current = self._row(row) or {}
            merged = {k: current.get(k) for k in LEAD_FIELDS}
            merged.update({k: v for k, v in fields.items() if k in LEAD_FIELDS and v not in (None, "")})
            ids = list(dict.fromkeys((current.get("interested_property_ids") or []) + (interested_ids or [])))
            lead_id = current.get("id") or str(uuid.uuid4())
            score, points, reasons = score_lead(merged, self._has_visit(lead_id) if current else False)
            values = (merged["name"], merged["phone"], merged["zone"], merged["max_budget_mxn"], merged["bedrooms"],
                      merged["property_type"], merged["payment_method"], merged["timeline"], json.dumps(ids),
                      score, points, json.dumps(reasons, ensure_ascii=False))
            if current:
                self._conn.execute(
                    """UPDATE leads SET name=?, phone=?, zone=?, max_budget_mxn=?, bedrooms=?, property_type=?,
                       payment_method=?, timeline=?, interested_property_ids=?, score=?, score_points=?,
                       score_reasons=?, updated_at=? WHERE id=?""",
                    (*values, now, lead_id),
                )
            else:
                self._conn.execute(
                    """INSERT INTO leads (name, phone, zone, max_budget_mxn, bedrooms, property_type, payment_method,
                       timeline, interested_property_ids, score, score_points, score_reasons, id, session_id,
                       created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (*values, lead_id, session_id, now, now),
                )
            self._conn.commit()
            row = self._conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return self._row(row)

    def add_visit(self, lead_id: str, property_id: int, property_name: str, preferred_date: str | None) -> dict:
        visit = {"id": str(uuid.uuid4()), "lead_id": lead_id, "property_id": property_id,
                 "property_name": property_name, "preferred_date": preferred_date, "status": "solicitada",
                 "created_at": iso(utcnow())}
        with self._lock:
            self._conn.execute(
                "INSERT INTO visits (id, lead_id, property_id, property_name, preferred_date, status, created_at) "
                "VALUES (:id, :lead_id, :property_id, :property_name, :preferred_date, :status, :created_at)", visit)
            self._conn.commit()
        return visit

    def rescore(self, lead_id: str) -> dict:
        with self._lock:
            lead = self._row(self._conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone())
            score, points, reasons = score_lead(lead, self._has_visit(lead_id))
            self._conn.execute("UPDATE leads SET score=?, score_points=?, score_reasons=?, updated_at=? WHERE id=?",
                               (score, points, json.dumps(reasons, ensure_ascii=False), iso(utcnow()), lead_id))
            self._conn.commit()
            return self._row(self._conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone())

    def list_leads(self, since: datetime | None = None, score: str | None = None, limit: int = 50) -> list[dict]:
        sql, args = "SELECT * FROM leads WHERE 1=1", []
        if since is not None:
            sql += " AND created_at >= ?"
            args.append(iso(since))
        if score in SCORES:
            sql += " AND score = ?"
            args.append(score)
        sql += " ORDER BY created_at DESC LIMIT ?"
        args.append(max(1, min(limit, 500)))
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
            leads = [self._row(r) for r in rows]
            for lead in leads:
                visits = self._conn.execute(
                    "SELECT property_id, property_name, preferred_date, status, created_at FROM visits "
                    "WHERE lead_id = ? ORDER BY created_at", (lead["id"],)).fetchall()
                lead["visits"] = [dict(v) for v in visits]
        return leads

    def stats(self, since: datetime | None = None) -> dict:
        leads = self.list_leads(since=since, limit=500)
        by_score = {s: 0 for s in SCORES}
        zones: dict[str, int] = {}
        budgets = []
        visits = 0
        for lead in leads:
            by_score[lead["score"]] = by_score.get(lead["score"], 0) + 1
            if lead.get("zone"):
                zones[lead["zone"]] = zones.get(lead["zone"], 0) + 1
            if lead.get("max_budget_mxn"):
                budgets.append(lead["max_budget_mxn"])
            visits += len(lead["visits"])
        budgets.sort()
        return {
            "total_leads": len(leads),
            "by_score": by_score,
            "with_contact": sum(1 for lead in leads if lead.get("phone")),
            "visits_requested": visits,
            "top_zones": sorted(zones.items(), key=lambda kv: (-kv[1], kv[0]))[:5],
            "budget_mxn": {"min": budgets[0], "median": budgets[len(budgets) // 2], "max": budgets[-1]}
            if budgets else None,
        }


def since_from_label(label: str | None, tz: timezone) -> datetime | None:
    """'today' = desde la medianoche local (Ciudad de México); '7d' = últimos 7 días; 'all' = sin filtro."""
    if label in (None, "", "all"):
        return None
    now_local = datetime.now(tz)
    if label == "today":
        return now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    if label == "7d":
        return now_local - timedelta(days=7)
    raise ValueError(label)
