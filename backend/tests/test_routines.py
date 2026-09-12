"""ETAPA 12 — rotina de referência e eventos de vida (itens 4/11/33/56/57)."""
import datetime

from tests.conftest import register_and_login as _register_and_login

OWNER_EMAIL = "rotina@example.com"
OWNER_PASSWORD = "senhaForte123"


def test_get_current_routine_before_creation_is_404(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    assert client.get("/api/v1/routines/current", headers=headers).status_code == 404


def test_create_routine(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post(
        "/api/v1/routines",
        json={
            "typical_wake_time": "07:00:00",
            "typical_sleep_time": "23:30:00",
            "goes_out_on_weekdays": True,
            "social_contact_days_per_week": 5,
            "selected_activation_domains": ["higiene", "trabalho"],
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["version"] == 1
    assert body["period_end"] is None
    assert body["typical_wake_time"] == "07:00:00"
    assert body["selected_activation_domains"] == ["higiene", "trabalho"]


def test_cannot_create_a_second_routine_while_one_is_active(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/routines", json={}, headers=headers)
    response = client.post("/api/v1/routines", json={}, headers=headers)
    assert response.status_code == 409


def test_patch_logs_routine_event_per_changed_field(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/routines", json={"social_contact_days_per_week": 5}, headers=headers)

    response = client.patch(
        "/api/v1/routines/current",
        json={"social_contact_days_per_week": 2, "goes_out_on_weekdays": False},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["social_contact_days_per_week"] == 2
    assert body["version"] == 1  # PATCH nunca cria versão nova

    events = client.get("/api/v1/routines/current/events", headers=headers).json()
    changed_fields = {e["changed_field"] for e in events}
    assert changed_fields == {"social_contact_days_per_week", "goes_out_on_weekdays"}
    social_event = next(e for e in events if e["changed_field"] == "social_contact_days_per_week")
    assert social_event["old_value"] == "5"
    assert social_event["new_value"] == "2"


def test_patch_with_same_value_does_not_log_event(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/routines", json={"social_contact_days_per_week": 5}, headers=headers)
    client.patch("/api/v1/routines/current", json={"social_contact_days_per_week": 5}, headers=headers)

    events = client.get("/api/v1/routines/current/events", headers=headers).json()
    assert events == []


def test_new_version_closes_previous_and_does_not_erase_history(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/routines", json={"social_contact_days_per_week": 5}, headers=headers)

    response = client.post(
        "/api/v1/routines/new-version",
        json={"social_contact_days_per_week": 1, "notes": "novo emprego, rotina mudou bastante"},
        headers=headers,
    )
    assert response.status_code == 201
    new_routine = response.json()
    assert new_routine["version"] == 2
    assert new_routine["period_end"] is None
    assert new_routine["social_contact_days_per_week"] == 1

    history = client.get("/api/v1/routines", headers=headers).json()
    assert len(history) == 2
    old = next(r for r in history if r["version"] == 1)
    assert old["period_end"] is not None  # a versão antiga foi fechada, não apagada


def test_routine_is_private_to_its_owner(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/routines", json={}, headers=owner_headers)

    other_headers = _register_and_login(client, "outra-rotina@example.com", "outraSenhaForte123")
    assert client.get("/api/v1/routines/current", headers=other_headers).status_code == 404
    assert client.get("/api/v1/routines", headers=other_headers).json() == []


def test_life_event_create_and_list(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post(
        "/api/v1/life-events",
        json={"event_type": "new_job", "description": "novo emprego", "start_date": "2026-01-10"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["event_type"] == "new_job"

    listing = client.get("/api/v1/life-events", headers=headers).json()
    assert len(listing) == 1


def test_life_events_are_private_to_their_owner(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post(
        "/api/v1/life-events",
        json={"event_type": "travel", "start_date": "2026-02-01"},
        headers=owner_headers,
    )
    other_headers = _register_and_login(client, "outra-vida@example.com", "outraSenhaForte123")
    assert client.get("/api/v1/life-events", headers=other_headers).json() == []
