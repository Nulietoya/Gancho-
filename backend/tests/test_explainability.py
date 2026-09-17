"""
ETAPA 20 — explicabilidade (itens 15/22). Cobre a decomposição de um
`DeviationEvent` por indicador (baseline vs. valor recente, direção,
dias seguidos) e a agregação por `Alert` (quantos motores convergiram,
de quantos possíveis).
"""
from tests.conftest import post_checkin as _post_checkin
from tests.conftest import register_and_login as _register_and_login

OWNER_EMAIL = "explain@example.com"
OWNER_PASSWORD = "senhaForte123"


def _build_mood_drop(client, headers):
    for days_ago in range(12, 2, -1):
        _post_checkin(client, headers, days_ago, mood=4)
    for days_ago in (2, 1, 0):
        _post_checkin(client, headers, days_ago, mood=1)


def test_explain_deviation_event_breaks_down_indicators(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _build_mood_drop(client, headers)
    event = client.post("/api/v1/deviation/run/stability", headers=headers).json()

    response = client.get(f"/api/v1/deviation/events/{event['id']}/explanation", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["engine"] == "stability"
    assert body["engine_label"] == "estabilidade"
    assert body["duration_days"] == 3

    mood = next(i for i in body["indicators"] if i["indicator_key"] == "mood")
    assert mood["label"] == "seu humor"
    assert mood["recent_value"] == 1.0
    assert mood["direction"] == "abaixo do seu padrão habitual"
    assert mood["streak_days"] == 3
    assert round(mood["baseline_mean"], 2) == 3.31

    # respaldo científico (pedido do usuário): texto fixo por motor,
    # nunca um número novo — ver app/services/psychoeducation.py
    assert body["scientific_context"]
    assert "sono" in body["scientific_context"].lower() or "medica" in body["scientific_context"].lower()


def test_explain_deviation_event_not_found_is_404(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/deviation/events/{fake_id}/explanation", headers=headers)
    assert response.status_code == 404


def test_explain_alert_aggregates_converging_engines(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    for days_ago in range(12, 2, -1):
        _post_checkin(client, headers, days_ago, mood=4, energy=4)
    for days_ago in (2, 1, 0):
        _post_checkin(client, headers, days_ago, mood=1, energy=1)
    client.post("/api/v1/deviation/run", headers=headers)

    alert = client.post("/api/v1/alerts/sync", headers=headers).json()
    assert alert["state"] == "red"

    response = client.get(f"/api/v1/alerts/{alert['id']}/explanation", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["alert_id"] == alert["id"]
    assert body["state"] == "red"
    assert body["engines_count"] == 2
    assert body["total_engines"] == 4
    assert body["breadth_score"] == 0.5

    engines_seen = {e["engine"] for e in body["engines"]}
    assert engines_seen == {"stability", "activation"}
    for engine_explanation in body["engines"]:
        assert len(engine_explanation["indicators"]) >= 1
        assert engine_explanation["explanation"].startswith("Sua rotina mudou")


def test_explain_alert_green_has_no_engines(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    alert = client.post("/api/v1/alerts/sync", headers=headers).json()

    response = client.get(f"/api/v1/alerts/{alert['id']}/explanation", headers=headers)
    body = response.json()
    assert body["state"] == "green"
    assert body["engines"] == []
    assert body["engines_count"] == 0
    assert body["breadth_score"] == 0.0


def test_explain_alert_not_found_is_404(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/alerts/{fake_id}/explanation", headers=headers)
    assert response.status_code == 404


def test_explanations_are_private_to_their_owner(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _build_mood_drop(client, owner_headers)
    event = client.post("/api/v1/deviation/run/stability", headers=owner_headers).json()
    alert = client.post("/api/v1/alerts/sync", headers=owner_headers).json()

    other_headers = _register_and_login(client, "outro-explain@example.com", "outraSenhaForte123")
    assert client.get(f"/api/v1/deviation/events/{event['id']}/explanation", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/alerts/{alert['id']}/explanation", headers=other_headers).status_code == 404
