"""Tools del agente con mínimo privilegio: leen el catálogo y escriben solo el lead de la sesión que llama."""

from __future__ import annotations

import logging
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from .catalog import PROPERTY_TYPES, AmbiguousAmountError, Catalog
from .leads import PAYMENT_METHODS, TIMELINES, LeadStore, normalize_mx_phone
from .llm.base import ToolCall, ToolSpec

log = logging.getLogger("inmobot.tools")


@dataclass
class ToolOutcome:
    content: dict[str, Any]
    is_error: bool = False
    cards: list[dict] | None = None  # None = esta tool no cambia las tarjetas visibles
    actions: list[dict] = field(default_factory=list)
    lead_saved: bool = False


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("bool")
    if isinstance(value, (int, float)):
        return int(value)
    cleaned = str(value).replace(",", "").replace("$", "").strip()
    return int(float(cleaned))


def _enum_or_none(value: Any, allowed: tuple[str, ...]) -> str | None:
    if value in (None, ""):
        return None
    v = str(value).strip().lower()
    if v not in allowed:
        raise ValueError(f"valor no permitido: {value}")
    return v


def build_tool_specs(catalog: Catalog) -> list[ToolSpec]:
    zone = {"type": "string", "enum": catalog.zones, "description": "Zona del catálogo"}
    ptype = {"type": "string", "enum": list(PROPERTY_TYPES)}
    return [
        ToolSpec(
            "search_properties",
            "Busca propiedades en el catálogo. Devuelve coincidencias (máximo 3) o alternativas cercanas. "
            "Los resultados se muestran al usuario como tarjetas.",
            {"type": "object", "properties": {
                "zone": zone,
                "max_price_mxn": {"type": "integer",
                                  "description": "Presupuesto máximo en pesos, número completo (ej. 2500000)"},
                "min_price_mxn": {"type": "integer", "description": "Precio mínimo en pesos, número completo"},
                "min_bedrooms": {"type": "integer", "description": "Recámaras mínimas"},
                "property_type": ptype,
            }},
        ),
        ToolSpec(
            "get_property",
            "Devuelve los detalles de una propiedad del catálogo por su id (amenidades, descripción).",
            {"type": "object", "properties": {"property_id": {"type": "integer"}}, "required": ["property_id"]},
        ),
        ToolSpec(
            "save_lead",
            "Guarda o actualiza los datos del prospecto de esta conversación. Llámala en cuanto tengas nombre y "
            "teléfono, con todo lo que sepas. El teléfono debe tener 10 dígitos de México.",
            {"type": "object", "properties": {
                "name": {"type": "string", "description": "Nombre del prospecto"},
                "phone": {"type": "string", "description": "Teléfono de 10 dígitos"},
                "zone": zone,
                "max_budget_mxn": {"type": "integer", "description": "Presupuesto máximo en pesos"},
                "bedrooms": {"type": "integer"},
                "property_type": ptype,
                "payment_method": {"type": "string", "enum": list(PAYMENT_METHODS)},
                "timeline": {"type": "string", "enum": list(TIMELINES),
                             "description": "Plazo para comprar"},
                "interested_property_ids": {"type": "array", "items": {"type": "integer"}},
            }},
        ),
        ToolSpec(
            "request_visit",
            "Registra una SOLICITUD de visita a una propiedad del catálogo para el prospecto de esta conversación. "
            "Requiere save_lead con nombre y teléfono. Un asesor confirma la fecha.",
            {"type": "object", "properties": {
                "property_id": {"type": "integer"},
                "preferred_date": {"type": "string",
                                   "description": "Preferencia en texto libre, ej. 'sábado por la mañana'"},
            }, "required": ["property_id"]},
        ),
        ToolSpec(
            "handoff_to_human",
            "Ofrece continuar con un asesor humano por WhatsApp. Devuelve un botón con el resumen del prospecto.",
            {"type": "object", "properties": {"reason": {"type": "string", "description": "Motivo breve"}}},
        ),
    ]


class ToolExecutor:
    def __init__(self, catalog: Catalog, leads: LeadStore, whatsapp_number: str | None):
        self.catalog = catalog
        self.leads = leads
        self.whatsapp_number = whatsapp_number
        # Criterios de la última búsqueda por sesión: el lead hereda lo que de verdad se buscó.
        self._criteria: dict[str, dict] = {}

    def forget(self, session_id: str) -> None:
        self._criteria.pop(session_id, None)

    def execute(self, call: ToolCall, session_id: str) -> ToolOutcome:
        handler = getattr(self, f"_t_{call.name}", None)
        if handler is None:
            return ToolOutcome({"error": f"Herramienta desconocida: {call.name}"}, is_error=True)
        try:
            return handler(call.args or {}, session_id)
        except (ValueError, TypeError) as exc:
            log.info("tool_error", extra={"tool": call.name, "kind": type(exc).__name__})
            return ToolOutcome({"error": f"Argumentos inválidos: {exc}"}, is_error=True)

    # --- tools -------------------------------------------------------------------------------------------
    def _t_search_properties(self, args: dict, session_id: str) -> ToolOutcome:
        zone_in = args.get("zone")
        zone = self.catalog.normalize_zone(zone_in)
        if zone_in and not zone:
            return ToolOutcome({"count": 0, "properties": [], "error": f"Zona fuera del catálogo: {zone_in}",
                                "available_zones": self.catalog.zones}, is_error=True, cards=[])
        max_price = _int_or_none(args.get("max_price_mxn"))
        min_price = _int_or_none(args.get("min_price_mxn"))
        min_bedrooms = _int_or_none(args.get("min_bedrooms"))
        ptype = _enum_or_none(args.get("property_type"), PROPERTY_TYPES)
        try:
            result = self.catalog.search(zone, max_price, min_price, min_bedrooms, ptype)
        except AmbiguousAmountError as exc:
            return ToolOutcome({"error": f"Monto ambiguo ({exc}). Confirma con el usuario el monto completo en "
                                         "pesos (por ejemplo, ¿3 millones?) antes de buscar."}, is_error=True)
        criteria = {"zone": zone, "max_budget_mxn": max_price, "bedrooms": min_bedrooms, "property_type": ptype}
        self._criteria[session_id] = {**self._criteria.get(session_id, {}),
                                      **{k: v for k, v in criteria.items() if v is not None}}
        cards = [p.card() for p in result.matches] + [p.card(alternative=True) for p in result.alternatives]
        content = {
            "count": len(result.matches),
            "properties": [p.summary() for p in result.matches],
            "alternatives": [p.summary() for p in result.alternatives],
            "relaxed_criteria": result.relaxed,
            "note": "El usuario ya ve estas propiedades como tarjetas; no repitas sus datos.",
        }
        return ToolOutcome(content, cards=cards)

    def _t_get_property(self, args: dict, session_id: str) -> ToolOutcome:
        pid = _int_or_none(args.get("property_id"))
        prop = self.catalog.get(pid) if pid is not None else None
        if prop is None:
            return ToolOutcome({"error": f"No existe la propiedad {pid} en el catálogo."}, is_error=True)
        return ToolOutcome({"property": prop.details()}, cards=[prop.card()])

    def _t_save_lead(self, args: dict, session_id: str) -> ToolOutcome:
        fields: dict[str, Any] = {}
        if args.get("name"):
            name = " ".join(str(args["name"]).split())[:80]
            if len(name) < 2:
                raise ValueError("nombre demasiado corto")
            fields["name"] = name
        if args.get("phone"):
            phone = normalize_mx_phone(str(args["phone"]))
            if phone is None:
                return ToolOutcome({"saved": False, "error": "Teléfono inválido: pide 10 dígitos de México."},
                                   is_error=True)
            fields["phone"] = phone
        zone = self.catalog.normalize_zone(args.get("zone"))
        if zone:
            fields["zone"] = zone
        budget = _int_or_none(args.get("max_budget_mxn"))
        if budget is not None:
            try:
                fields["max_budget_mxn"] = Catalog.check_amount(budget)
            except AmbiguousAmountError:
                return ToolOutcome({"saved": False, "error": "Presupuesto ambiguo: confirma el monto completo."},
                                   is_error=True)
        bedrooms = _int_or_none(args.get("bedrooms"))
        if bedrooms is not None:
            fields["bedrooms"] = bedrooms
        for key, allowed in (("property_type", PROPERTY_TYPES), ("payment_method", PAYMENT_METHODS),
                             ("timeline", TIMELINES)):
            value = _enum_or_none(args.get(key), allowed)
            if value:
                fields[key] = value
        for key, value in self._criteria.get(session_id, {}).items():
            fields.setdefault(key, value)
        ids = [i for i in (_int_or_none(x) for x in (args.get("interested_property_ids") or []))
               if i is not None and self.catalog.get(i)]
        if not fields and not ids:
            return ToolOutcome({"saved": False, "error": "No hay datos que guardar."}, is_error=True)
        lead = self.leads.upsert_lead(session_id, fields, ids)
        missing = [k for k in ("name", "phone", "payment_method", "timeline") if not lead.get(k)]
        return ToolOutcome({"saved": True, "missing_fields": missing}, lead_saved=True)

    def _t_request_visit(self, args: dict, session_id: str) -> ToolOutcome:
        pid = _int_or_none(args.get("property_id"))
        prop = self.catalog.get(pid) if pid is not None else None
        if prop is None:
            return ToolOutcome({"error": f"No existe la propiedad {pid} en el catálogo."}, is_error=True)
        lead = self.leads.get_by_session(session_id)
        if not lead or not lead.get("name") or not lead.get("phone"):
            return ToolOutcome({"error": "Primero pide nombre y teléfono y llama a save_lead."}, is_error=True)
        preferred = " ".join(str(args.get("preferred_date") or "").split())[:80] or None
        self.leads.upsert_lead(session_id, {}, [prop.id])
        visit = self.leads.add_visit(lead["id"], prop.id, prop.name, preferred)
        self.leads.rescore(lead["id"])
        action = {"type": "visit_requested", "property_id": prop.id, "property_name": prop.name,
                  "preferred_date": preferred}
        return ToolOutcome({"status": visit["status"], "property": prop.name, "preferred_date": preferred,
                            "next_step": "Un asesor confirmará fecha y hora por WhatsApp o teléfono."},
                           actions=[action], lead_saved=True)

    def _t_handoff_to_human(self, args: dict, session_id: str) -> ToolOutcome:
        if not self.whatsapp_number:
            return ToolOutcome({"available": False,
                                "message": "WhatsApp no configurado; un asesor contactará al teléfono registrado."})
        return ToolOutcome({"available": True, "note": "Se mostró un botón de WhatsApp al usuario."},
                           actions=[self.whatsapp_action(session_id)])

    def whatsapp_action(self, session_id: str | None) -> dict:
        lead = self.leads.get_by_session(session_id) if session_id else None
        parts = ["Hola, vengo del chat de InmoBot (demo)."]
        if lead:
            if lead.get("name"):
                parts.append(f"Soy {lead['name']}.")
            interest = [self.catalog.get(i) for i in lead.get("interested_property_ids") or []]
            names = ", ".join(p.name for p in interest if p)
            if names:
                parts.append(f"Me interesa: {names}.")
            elif lead.get("zone"):
                parts.append(f"Busco en {lead['zone']}.")
            if lead.get("max_budget_mxn"):
                parts.append(f"Presupuesto: ${lead['max_budget_mxn']:,} MXN.")
            parts.append(f"Ref. {lead['id'][:8]}")
        text = " ".join(parts)
        url = f"https://wa.me/{self.whatsapp_number}?text={urllib.parse.quote(text)}"
        return {"type": "whatsapp", "url": url, "label": "Continuar por WhatsApp"}
