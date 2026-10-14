from app.llm.base import ToolCall
from app.tools import ToolExecutor


def run(executor, name, args, sid="s1"):
    return executor.execute(ToolCall(id="c1", name=name, args=args), sid)


def test_search_produces_cards_from_catalog(catalog, leads):
    ex = ToolExecutor(catalog, leads, "5210000000000")
    out = run(ex, "search_properties", {"zone": "Cholula", "max_price_mxn": 2500000.0, "min_bedrooms": 3,
                                         "property_type": "casa"})
    assert not out.is_error and [c["id"] for c in out.cards] == [4, 5]


def test_search_ambiguous_amount_asks_to_confirm(catalog, leads):
    out = run(ToolExecutor(catalog, leads, None), "search_properties", {"zone": "Cholula", "max_price_mxn": 3})
    assert out.is_error and "ambiguo" in out.content["error"].lower() and out.cards is None


def test_search_unknown_zone_returns_available_zones_and_no_cards(catalog, leads):
    out = run(ToolExecutor(catalog, leads, None), "search_properties", {"zone": "Atlixco"})
    assert out.is_error and out.cards == [] and "Cholula" in out.content["available_zones"]


def test_save_lead_rejects_invalid_phone(catalog, leads):
    out = run(ToolExecutor(catalog, leads, None), "save_lead", {"name": "Ana", "phone": "123"})
    assert out.is_error and leads.get_by_session("s1") is None


def test_save_lead_inherits_search_criteria(catalog, leads):
    ex = ToolExecutor(catalog, leads, None)
    run(ex, "search_properties", {"zone": "Cholula", "max_price_mxn": 2500000, "min_bedrooms": 3})
    out = run(ex, "save_lead", {"name": "Ana Prueba", "phone": "2221234567", "payment_method": "contado",
                                "timeline": "1_3_meses"})
    lead = leads.get_by_session("s1")
    assert out.lead_saved and lead["zone"] == "Cholula" and lead["max_budget_mxn"] == 2500000
    assert lead["score"] == "caliente"


def test_visit_requires_contact_first(catalog, leads):
    out = run(ToolExecutor(catalog, leads, None), "request_visit", {"property_id": 4})
    assert out.is_error and "save_lead" in out.content["error"]


def test_visit_records_request_and_action(catalog, leads):
    ex = ToolExecutor(catalog, leads, None)
    run(ex, "save_lead", {"name": "Ana Prueba", "phone": "2221234567"})
    out = run(ex, "request_visit", {"property_id": 4, "preferred_date": "sábado por la mañana"})
    assert not out.is_error and out.actions[0]["type"] == "visit_requested"
    assert leads.list_leads()[0]["visits"][0]["property_id"] == 4


def test_visit_to_unknown_property_fails(catalog, leads):
    ex = ToolExecutor(catalog, leads, None)
    run(ex, "save_lead", {"name": "Ana Prueba", "phone": "2221234567"})
    assert run(ex, "request_visit", {"property_id": 999}).is_error


def test_handoff_builds_wa_me_link_or_declines(catalog, leads):
    with_number = run(ToolExecutor(catalog, leads, "5210000000000"), "handoff_to_human", {})
    assert with_number.actions[0]["url"].startswith("https://wa.me/5210000000000?text=")
    without = run(ToolExecutor(catalog, leads, None), "handoff_to_human", {})
    assert without.actions == [] and without.content["available"] is False


def test_unknown_tool_is_an_error(catalog, leads):
    assert run(ToolExecutor(catalog, leads, None), "delete_all_leads", {}).is_error
