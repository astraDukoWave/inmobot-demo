import pytest

from app.leads import mask_phone, normalize_mx_phone, score_lead


@pytest.mark.parametrize("raw,expected", [
    ("222 123 4567", "+522221234567"), ("+52 222-123-4567", "+522221234567"), ("+521 2221234567", "+522221234567"),
    ("12345", None), ("0221234567", None), ("", None),
])
def test_phone_normalization(raw, expected):
    assert normalize_mx_phone(raw) == expected


def test_mask_phone_keeps_last_four_only():
    assert mask_phone("+522221234567") == "+52 ••• ••• 4567"


def test_ac05a_full_qualification_is_hot():
    lead = {"phone": "+522221234567", "max_budget_mxn": 2_500_000, "zone": "Cholula",
            "payment_method": "infonavit_fovissste", "timeline": "1_3_meses"}
    assert score_lead(lead, visit_requested=False)[0] == "caliente"


def test_no_phone_is_always_cold():
    lead = {"max_budget_mxn": 2_500_000, "zone": "Cholula", "payment_method": "contado", "timeline": "inmediato"}
    assert score_lead(lead, visit_requested=True)[0] == "frio"


def test_upsert_merges_one_lead_per_session(leads):
    leads.upsert_lead("s1", {"name": "Ana Prueba", "zone": "Cholula"})
    lead = leads.upsert_lead("s1", {"phone": "+522221234567", "timeline": "inmediato"})
    assert lead["name"] == "Ana Prueba" and lead["zone"] == "Cholula" and lead["phone"] == "+522221234567"
    assert len(leads.list_leads()) == 1


def test_visit_rescores_and_stats(leads):
    lead = leads.upsert_lead("s1", {"name": "Ana", "phone": "+522221234567", "zone": "Cholula"})
    leads.add_visit(lead["id"], 4, "Casa Los Fresnos", "sábado")
    lead = leads.rescore(lead["id"])
    assert "pidió visita (+2)" in lead["score_reasons"]
    stats = leads.stats()
    assert stats["total_leads"] == 1 and stats["visits_requested"] == 1 and stats["top_zones"][0][0] == "Cholula"
