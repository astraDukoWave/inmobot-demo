"""Catálogo de propiedades (ficticio). Búsqueda determinista: el LLM nunca filtra ni inventa propiedades."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

PROPERTY_TYPES = ("casa", "departamento")
MIN_PLAUSIBLE_PRICE_MXN = 100_000  # debajo de esto el monto es ambiguo ("3", "2.5") y se confirma (A7)


class AmbiguousAmountError(ValueError):
    pass


def normalize_text(text: str) -> str:
    stripped = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(stripped.lower().split())


@dataclass(frozen=True)
class Property:
    id: int
    name: str
    zone: str
    type: str
    price_mxn: int
    bedrooms: int
    bathrooms: int
    area_m2: int
    amenities: tuple[str, ...]
    description: str
    image_url: str

    def summary(self) -> dict:
        """Lo que recibe el modelo: datos para conversar, sin descripción larga."""
        return {
            "id": self.id,
            "name": self.name,
            "zone": self.zone,
            "type": self.type,
            "price_mxn": self.price_mxn,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "area_m2": self.area_m2,
        }

    def details(self) -> dict:
        return {**self.summary(), "amenities": list(self.amenities), "description": self.description}

    def card(self, alternative: bool = False) -> dict:
        """Lo que pinta la UI. Sale del catálogo, nunca del texto del modelo."""
        return {**self.summary(), "amenities": list(self.amenities), "image_url": self.image_url,
                "alternative": alternative}


@dataclass(frozen=True)
class SearchResult:
    matches: list[Property]
    alternatives: list[Property]
    relaxed: list[str]


class Catalog:
    def __init__(self, properties: list[Property]):
        self._by_id = {p.id: p for p in properties}
        self.properties = sorted(properties, key=lambda p: p.id)
        self.zones = sorted({p.zone for p in properties})
        self._zone_lookup = {normalize_text(z): z for z in self.zones}
        aliases = {"lomas": "Lomas de Angelópolis", "san andres cholula": "Cholula",
                   "san pedro cholula": "Cholula", "centro historico": "Centro"}
        for alias, zone in aliases.items():
            if zone in self.zones:
                self._zone_lookup.setdefault(alias, zone)

    @classmethod
    def load(cls, path: str | Path) -> Catalog:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        props = [
            Property(
                id=int(p["id"]), name=p["name"], zone=p["zone"], type=p["type"], price_mxn=int(p["price_mxn"]),
                bedrooms=int(p["bedrooms"]), bathrooms=int(p["bathrooms"]), area_m2=int(p["area_m2"]),
                amenities=tuple(p.get("amenities", [])), description=p.get("description", ""),
                image_url=p.get("image_url", ""),
            )
            for p in raw
        ]
        return cls(props)

    def get(self, property_id: int) -> Property | None:
        return self._by_id.get(property_id)

    def normalize_zone(self, zone: str | None) -> str | None:
        if not zone:
            return None
        return self._zone_lookup.get(normalize_text(zone))

    @staticmethod
    def check_amount(value: int | None) -> int | None:
        if value is None:
            return None
        if value < MIN_PLAUSIBLE_PRICE_MXN:
            raise AmbiguousAmountError(value)
        return value

    def _filter(self, zone, min_price, max_price, min_bedrooms, ptype) -> list[Property]:
        out = []
        for p in self.properties:
            if zone and p.zone != zone:
                continue
            if max_price is not None and p.price_mxn > max_price:
                continue
            if min_price is not None and p.price_mxn < min_price:
                continue
            if min_bedrooms is not None and p.bedrooms < min_bedrooms:
                continue
            if ptype and p.type != ptype:
                continue
            out.append(p)
        # Más cerca del presupuesto primero (aprovecha el presupuesto); sin presupuesto, más barato primero.
        if max_price is not None:
            return sorted(out, key=lambda p: (max_price - p.price_mxn, p.id))
        return sorted(out, key=lambda p: (p.price_mxn, p.id))

    def search(self, zone: str | None = None, max_price: int | None = None, min_price: int | None = None,
               min_bedrooms: int | None = None, property_type: str | None = None, limit: int = 3) -> SearchResult:
        """Coincidencias exactas; si no hay, alternativas por relajación determinista y declarada."""
        max_price = self.check_amount(max_price)
        min_price = self.check_amount(min_price)
        ptype = property_type if property_type in PROPERTY_TYPES else None
        matches = self._filter(zone, min_price, max_price, min_bedrooms, ptype)
        if matches:
            return SearchResult(matches[:limit], [], [])
        steps = [
            ("recámaras", dict(zone=zone, min_price=min_price, max_price=max_price, min_bedrooms=None, ptype=ptype)),
            ("tipo", dict(zone=zone, min_price=min_price, max_price=max_price, min_bedrooms=None, ptype=None)),
            ("presupuesto +15%", dict(zone=zone, min_price=None,
                                      max_price=int(max_price * 1.15) if max_price else None,
                                      min_bedrooms=None, ptype=None)),
            ("zona", dict(zone=None, min_price=None, max_price=max_price, min_bedrooms=min_bedrooms, ptype=ptype)),
        ]
        relaxed: list[str] = []
        for label, kwargs in steps:
            relaxed.append(label)
            alt = self._filter(kwargs["zone"], kwargs["min_price"], kwargs["max_price"],
                               kwargs["min_bedrooms"], kwargs["ptype"])
            if alt:
                return SearchResult([], alt[:2], relaxed)
        return SearchResult([], [], relaxed)
