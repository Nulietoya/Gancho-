"""
ETAPA 17 — motor de baseline (itens 5/32/38/56/57). Cobre a ingestão
automática em `FunctionalIndicator` a partir de check-in/tarefa/
medicação, o cálculo de baseline em si, e a virada de versão.
"""
import datetime

from tests.conftest import register_and_login as _register_and_login

OWNER_EMAIL = "baseline@example.com"
OWNER_PASSWORD = "senhaForte123"


def test_checkin_feeds_functional_indicator(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/checkins", json={"mood": 4, "energy": 3, "anxiety": 2}, headers=headers)

    values = client.get("/api/v1/indicators?indicator_key=mood", headers=headers).json()
    assert len(values) == 1
    assert values[0]["value"] == 4.0
    assert values[0]["source"] == "checkin"

    # sleep_quality não tem IndicatorKey correspondente ainda — não deve gerar indicador
    assert client.get("/api/v1/indicators?indicator_key=energy", headers=headers).json()[0]["value"] == 3.0


def test_checkin_patch_updates_the_indicator_value(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/checkins", json={"mood": 2}, headers=headers)
    today = datetime.date.today().isoformat()
    client.patch(f"/api/v1/checkins/{today}", json={"mood": 5}, headers=headers)

    values = client.get("/api/v1/indicators?indicator_key=mood", headers=headers).json()
    assert len(values) == 1  # upsert, não duplica
    assert values[0]["value"] == 5.0


def test_checkin_patch_clearing_a_field_deletes_the_stale_indicator(client):
    """
    Regressão: limpar um campo do check-in (`{"mood": null}`) tem que
    apagar o `FunctionalIndicator` daquele dia, não deixar o valor
    antigo parado — "sem dado" nunca pode virar silenciosamente
    "o último dado que existiu".
    """
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/checkins", json={"mood": 2, "energy": 3}, headers=headers)
    today = datetime.date.today().isoformat()
    client.patch(f"/api/v1/checkins/{today}", json={"mood": None}, headers=headers)

    assert client.get("/api/v1/indicators?indicator_key=mood", headers=headers).json() == []
    # campo não tocado no PATCH continua intacto
    assert client.get("/api/v1/indicators?indicator_key=energy", headers=headers).json()[0]["value"] == 3.0


def test_task_events_feed_functional_indicator(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = client.post("/api/v1/tasks", json={"title": "lavar louça"}, headers=headers).json()
    client.post(f"/api/v1/tasks/{task['id']}/start", headers=headers)
    client.post(f"/api/v1/tasks/{task['id']}/complete", headers=headers)

    started = client.get("/api/v1/indicators?indicator_key=tasks_started_count", headers=headers).json()
    completed = client.get("/api/v1/indicators?indicator_key=tasks_completed_count", headers=headers).json()
    assert started[0]["value"] == 1.0
    assert completed[0]["value"] == 1.0


def test_medication_adherence_indicator(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = client.post("/api/v1/medications", json={"name": "sertralina"}, headers=headers).json()
    schedule = client.post(
        f"/api/v1/medications/{med['id']}/schedules", json={"time_of_day": "08:00:00"}, headers=headers
    ).json()

    client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "taken"},
        headers=headers,
    )
    values = client.get("/api/v1/indicators?indicator_key=medication_adherence", headers=headers).json()
    assert values[0]["value"] == 1.0


def test_recompute_baseline_before_any_data_is_rejected(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post("/api/v1/baseline/mood/recompute", headers=headers)
    assert response.status_code == 409


def test_recompute_baseline_creates_version_one_and_metric(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/checkins", json={"mood": 3}, headers=headers)

    response = client.post("/api/v1/baseline/mood/recompute", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["status"] == "active"
    assert body["latest_metric"]["sample_size"] == 1
    assert body["latest_metric"]["mean"] == 3.0
    assert body["latest_metric"]["recent_value"] == 3.0
    assert body["latest_metric"]["diff_from_baseline"] == 0.0


def test_recompute_again_appends_metric_without_new_version(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/checkins", json={"mood": 3}, headers=headers)
    client.post("/api/v1/baseline/mood/recompute", headers=headers)

    second = client.post("/api/v1/baseline/mood/recompute", headers=headers)
    assert second.json()["version"] == 1

    history = client.get("/api/v1/baseline/mood/history", headers=headers).json()
    assert len(history) == 1
    assert len(history[0]["metrics"]) == 2


def test_get_baseline_before_recompute_is_404(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.get("/api/v1/baseline/mood", headers=headers)
    assert response.status_code == 404


def test_list_active_baselines(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/checkins", json={"mood": 3, "energy": 4}, headers=headers)
    client.post("/api/v1/baseline/mood/recompute", headers=headers)
    client.post("/api/v1/baseline/energy/recompute", headers=headers)

    listing = client.get("/api/v1/baseline", headers=headers).json()
    keys = {b["indicator_key"] for b in listing}
    assert keys == {"mood", "energy"}


def test_recalibrate_closes_previous_version_and_opens_new_one(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/checkins", json={"mood": 3}, headers=headers)
    client.post("/api/v1/baseline/mood/recompute", headers=headers)

    response = client.post("/api/v1/baseline/mood/recalibrate", headers=headers)
    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert response.json()["latest_metric"] is None

    history = client.get("/api/v1/baseline/mood/history", headers=headers).json()
    old = next(b for b in history if b["version"] == 1)
    assert old["status"] == "superseded"
    assert old["period_end"] is not None


def test_baseline_and_indicators_are_private_to_their_owner(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/checkins", json={"mood": 3}, headers=owner_headers)
    client.post("/api/v1/baseline/mood/recompute", headers=owner_headers)

    other_headers = _register_and_login(client, "outro-baseline@example.com", "outraSenhaForte123")
    assert client.get("/api/v1/indicators", headers=other_headers).json() == []
    assert client.get("/api/v1/baseline", headers=other_headers).json() == []
    assert client.get("/api/v1/baseline/mood", headers=other_headers).status_code == 404
