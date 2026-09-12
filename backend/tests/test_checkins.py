"""ETAPA 11 — check-in diário (item 6): curto, todo indicador opcional, um por dia."""
import datetime

from tests.conftest import register_and_login as _register_and_login

OWNER_EMAIL = "checkin@example.com"
OWNER_PASSWORD = "senhaForte123"


def test_empty_checkin_is_rejected(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post("/api/v1/checkins", json={}, headers=headers)
    assert response.status_code == 422


def test_create_checkin_defaults_to_today(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post("/api/v1/checkins", json={"mood": 3, "energy": 2}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["mood"] == 3
    assert body["energy"] == 2
    assert body["anxiety"] is None
    assert body["checkin_date"] == datetime.date.today().isoformat()


def test_only_one_checkin_per_day(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/checkins", json={"mood": 3}, headers=headers)
    response = client.post("/api/v1/checkins", json={"mood": 4}, headers=headers)
    assert response.status_code == 409


def test_patch_revises_todays_checkin(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    today = datetime.date.today().isoformat()
    client.post("/api/v1/checkins", json={"mood": 2, "sleep_quality": 2}, headers=headers)

    response = client.patch(f"/api/v1/checkins/{today}", json={"mood": 4}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["mood"] == 4
    assert body["sleep_quality"] == 2  # não enviado, não muda


def test_patch_on_missing_date_is_404(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.patch("/api/v1/checkins/2020-01-01", json={"mood": 4}, headers=headers)
    assert response.status_code == 404


def test_get_by_date_and_history_listing(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    client.post("/api/v1/checkins", json={"mood": 3, "checkin_date": yesterday}, headers=headers)
    client.post("/api/v1/checkins", json={"mood": 5}, headers=headers)

    got = client.get(f"/api/v1/checkins/{today}", headers=headers)
    assert got.status_code == 200
    assert got.json()["mood"] == 5

    history = client.get("/api/v1/checkins", headers=headers).json()
    assert len(history) == 2
    assert history[0]["checkin_date"] == today  # ordem desc


def test_history_listing_filters_by_date_from_and_date_to(client):
    """
    ETAPA 33-34: `date_from`/`date_to` de `GET /checkins` nunca tinham
    sido exercitados por nenhum teste (achado via `pytest --cov` —
    apareciam como linha morta em `checkin_service.list_checkins`).
    Três check-ins em dias diferentes, cada filtro isolado confere que
    exclui exatamente o que deveria.
    """
    headers = _register_and_login(client, "checkin-filtro@example.com", OWNER_PASSWORD)
    today = datetime.date.today()
    three_days_ago = (today - datetime.timedelta(days=3)).isoformat()
    one_day_ago = (today - datetime.timedelta(days=1)).isoformat()

    client.post("/api/v1/checkins", json={"mood": 1, "checkin_date": three_days_ago}, headers=headers)
    client.post("/api/v1/checkins", json={"mood": 2, "checkin_date": one_day_ago}, headers=headers)
    client.post("/api/v1/checkins", json={"mood": 3}, headers=headers)  # hoje

    only_from_yesterday = client.get(
        f"/api/v1/checkins?date_from={one_day_ago}", headers=headers
    ).json()
    assert {c["checkin_date"] for c in only_from_yesterday} == {one_day_ago, today.isoformat()}

    only_up_to_yesterday = client.get(
        f"/api/v1/checkins?date_to={one_day_ago}", headers=headers
    ).json()
    assert {c["checkin_date"] for c in only_up_to_yesterday} == {three_days_ago, one_day_ago}

    only_yesterday_exactly = client.get(
        f"/api/v1/checkins?date_from={one_day_ago}&date_to={one_day_ago}", headers=headers
    ).json()
    assert {c["checkin_date"] for c in only_yesterday_exactly} == {one_day_ago}


def test_checkins_are_private_to_their_owner(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/checkins", json={"mood": 3}, headers=owner_headers)

    other_headers = _register_and_login(client, "outro-checkin@example.com", "outraSenhaForte123")
    today = datetime.date.today().isoformat()
    response = client.get(f"/api/v1/checkins/{today}", headers=other_headers)
    assert response.status_code == 404
    assert client.get("/api/v1/checkins", headers=other_headers).json() == []


def test_extra_answers_alone_satisfy_minimum(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post(
        "/api/v1/checkins",
        json={"extra_answers": {"saiu_de_casa": True}},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["extra_answers"] == {"saiu_de_casa": True}
