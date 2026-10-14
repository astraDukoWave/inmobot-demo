import uuid

from app.llm import fake


def test_health(make_client):
    body = make_client().get("/health").json()
    assert body["status"] == "ok" and body["provider"] == "fake" and "key" not in str(body).lower()


def test_index_has_strict_csp(make_client):
    res = make_client().get("/")
    assert res.status_code == 200
    csp = res.headers["content-security-policy"]
    assert "script-src 'self'" in csp and "unsafe-inline" not in csp
    assert res.headers["x-content-type-options"] == "nosniff"


def test_chat_creates_server_side_uuid_session(make_client):
    client = make_client([fake.text("¡Hola!"), fake.text("¿Qué zona?")])
    first = client.post("/api/chat", json={"session_id": "session_123", "message": "hola"}).json()
    assert uuid.UUID(first["session_id"]).version == 4 and first["session_id"] != "session_123"
    second = client.post("/api/chat", json={"session_id": first["session_id"], "message": "casa"}).json()
    assert second["session_id"] == first["session_id"]


def test_chat_returns_cards_from_tools(make_client):
    client = make_client([fake.tool("search_properties", {"zone": "Cholula", "max_price_mxn": 2500000,
                                                          "min_bedrooms": 3}), fake.text("Mira estas opciones.")])
    body = client.post("/api/chat", json={"message": "Busco casa en Cholula"}).json()
    assert [c["id"] for c in body["cards"]] == [4, 5]


def test_message_too_long_and_empty(make_client):
    client = make_client()
    assert client.post("/api/chat", json={"message": "a" * 1001}).status_code == 422
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422


def test_rate_limit(make_client):
    client = make_client([fake.text("ok")] * 5, rate_limit_per_minute=2)
    codes = [client.post("/api/chat", json={"message": "hola"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_busy_session_returns_409(make_client):
    client = make_client([fake.text("ok")])
    sid = client.post("/api/chat", json={"message": "hola"}).json()["session_id"]
    session, _ = client.app.state.sessions.get_or_create(sid)
    session.lock.acquire()
    try:
        assert client.post("/api/chat", json={"session_id": sid, "message": "otra"}).status_code == 409
    finally:
        session.lock.release()


def test_admin_requires_token(make_client):
    client = make_client()
    assert client.get("/api/admin/leads").status_code == 401
    assert client.get("/api/admin/leads", headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = client.get("/api/admin/stats", headers={"Authorization": "Bearer test-admin-token"})
    assert ok.status_code == 200 and ok.json()["total_leads"] == 0


def test_admin_disabled_without_token(make_client):
    assert make_client(admin_token=None).get("/api/admin/leads").status_code == 503


def test_lead_flow_end_to_end_with_fake_llm(make_client):
    client = make_client([
        fake.tool("search_properties", {"zone": "Cholula", "max_price_mxn": 2500000, "min_bedrooms": 3}),
        fake.text("Mira estas opciones. ¿Cómo pagarías?"),
        fake.tool("save_lead", {"name": "Ana Prueba", "phone": "2221234567", "payment_method": "contado",
                                "timeline": "1_3_meses"}),
        fake.text("Gracias, Ana."),
        fake.tool("request_visit", {"property_id": 4, "preferred_date": "sábado"}),
        fake.text("Listo, solicitud registrada."),
    ])
    sid = client.post("/api/chat", json={"message": "Busco casa en Cholula"}).json()["session_id"]
    assert client.post("/api/chat", json={"session_id": sid, "message": "Contado, 2 meses; Ana 2221234567"}
                       ).json()["lead_saved"]
    visit = client.post("/api/chat", json={"session_id": sid, "message": "Visitar Los Fresnos"}).json()
    assert visit["actions"][0]["type"] == "visit_requested"
    leads = client.get("/api/admin/leads", headers={"Authorization": "Bearer test-admin-token"}).json()["leads"]
    assert leads[0]["score"] == "caliente" and leads[0]["visits"][0]["property_id"] == 4


def test_public_properties_endpoint(make_client):
    body = make_client().get("/api/properties", params={"zone": "cholula", "max_price_mxn": 2500000}).json()
    assert body["count"] == 3 and "phone" not in str(body)
