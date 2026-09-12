"""
ETAPA 19 — modelo de estado (item 20). Cobre VERDE por padrão,
AMARELO com um motor convergindo, VERMELHO com dois motores
convergindo ao mesmo tempo, a janela de relevância de um
`DeviationEvent` antigo, e o histórico nunca duplicando quando o
estado não muda.
"""
import datetime

from app.models.deviation import DeviationEvent
from app.models.enums import DeviationEngine
from tests.conftest import post_checkin, register_and_login, user_id

OWNER_EMAIL = "alerts@example.com"
OWNER_PASSWORD = "senhaForte123"


def _insert_deviation_event(db_session, owner_id, engine, detected_at, magnitude=2.0):
    event = DeviationEvent(
        user_id=owner_id,
        engine=engine,
        detected_at=detected_at,
        magnitude=magnitude,
        duration_days=3,
        domains_count=1,
        convergence_score=0.5,
        triggering_indicator_keys=["mood"],
        baseline_snapshot={"mood": {"mean": 3.0}},
        explanation="Sua rotina mudou: seu humor mudou por 3 dia(s) seguidos.",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def test_alert_defaults_to_green_with_no_deviation_events(client):
    headers = register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post("/api/v1/alerts/sync", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "green"
    assert body["triggering_deviation_id"] is None
    assert "Sem mudança" in body["reason_summary"]


def test_get_current_alert_before_sync_is_404(client):
    headers = register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.get("/api/v1/alerts/current", headers=headers)
    assert response.status_code == 404


def test_alert_becomes_yellow_after_real_deviation_from_engine(client):
    """Fluxo de ponta a ponta: check-in -> motor de desvio -> estado."""
    headers = register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    for days_ago in range(12, 2, -1):
        post_checkin(client, headers, days_ago, mood=4)
    for days_ago in (2, 1, 0):
        post_checkin(client, headers, days_ago, mood=1)

    deviation = client.post("/api/v1/deviation/run/stability", headers=headers).json()
    assert deviation is not None

    response = client.post("/api/v1/alerts/sync", headers=headers)
    body = response.json()
    assert body["state"] == "yellow"
    assert body["triggering_deviation_id"] == deviation["id"]

    current = client.get("/api/v1/alerts/current", headers=headers)
    assert current.status_code == 200
    assert current.json()["id"] == body["id"]


def test_alert_becomes_red_when_two_engines_converge(client, db_session):
    headers = register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = user_id(db_session, OWNER_EMAIL)
    now = datetime.datetime.now(datetime.timezone.utc)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.STABILITY, now, magnitude=1.8)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.EXECUTIVE, now, magnitude=2.5)

    response = client.post("/api/v1/alerts/sync", headers=headers)
    body = response.json()
    assert body["state"] == "red"
    assert "2 áreas" in body["reason_summary"]
    # o motor de maior magnitude é o representado como gatilho
    assert body["triggering_deviation_id"] is not None


def test_old_deviation_event_outside_window_does_not_count(client, db_session):
    headers = register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = user_id(db_session, OWNER_EMAIL)
    stale = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.STABILITY, stale)

    response = client.post("/api/v1/alerts/sync", headers=headers)
    assert response.json()["state"] == "green"


def test_sync_does_not_duplicate_history_when_state_is_unchanged(client):
    headers = register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/alerts/sync", headers=headers)
    client.post("/api/v1/alerts/sync", headers=headers)
    client.post("/api/v1/alerts/sync", headers=headers)

    history = client.get("/api/v1/alerts", headers=headers).json()
    assert len(history) == 1


def test_state_transition_appends_new_history_row(client, db_session):
    headers = register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/alerts/sync", headers=headers)  # green

    owner_id = user_id(db_session, OWNER_EMAIL)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.AVOIDANCE, datetime.datetime.now(datetime.timezone.utc))
    client.post("/api/v1/alerts/sync", headers=headers)  # yellow

    history = client.get("/api/v1/alerts", headers=headers).json()
    assert len(history) == 2
    assert [h["state"] for h in history] == ["yellow", "green"]  # mais recente primeiro


def test_acknowledge_and_resolve_are_idempotent(client):
    headers = register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    alert = client.post("/api/v1/alerts/sync", headers=headers).json()
    assert alert["acknowledged_at"] is None
    assert alert["resolved_at"] is None

    first_ack = client.post(f"/api/v1/alerts/{alert['id']}/acknowledge", headers=headers).json()
    assert first_ack["acknowledged_at"] is not None
    second_ack = client.post(f"/api/v1/alerts/{alert['id']}/acknowledge", headers=headers).json()
    assert second_ack["acknowledged_at"] == first_ack["acknowledged_at"]

    first_resolve = client.post(f"/api/v1/alerts/{alert['id']}/resolve", headers=headers).json()
    assert first_resolve["resolved_at"] is not None
    second_resolve = client.post(f"/api/v1/alerts/{alert['id']}/resolve", headers=headers).json()
    assert second_resolve["resolved_at"] == first_resolve["resolved_at"]


def test_acknowledge_nonexistent_alert_is_404(client):
    headers = register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(f"/api/v1/alerts/{fake_id}/acknowledge", headers=headers)
    assert response.status_code == 404


def test_alerts_are_private_to_their_owner(client):
    owner_headers = register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    alert = client.post("/api/v1/alerts/sync", headers=owner_headers).json()

    other_headers = register_and_login(client, "outro-alerts@example.com", "outraSenhaForte123")
    assert client.get("/api/v1/alerts", headers=other_headers).json() == []
    assert client.get("/api/v1/alerts/current", headers=other_headers).status_code == 404
    assert client.post(f"/api/v1/alerts/{alert['id']}/acknowledge", headers=other_headers).status_code == 404
