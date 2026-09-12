"""
ETAPA 18 — motor de desvio (itens 9-12/14/20/22). Cobre os quatro
motores, a exigência de amostra mínima de baseline, a exigência de
persistência (nunca dia isolado) e a regra de "zero real" pra
indicador de contagem vs. "buraco quebra a sequência" pra indicador
subjetivo/adesão.
"""
import datetime

from app.models.baseline import FunctionalIndicator
from app.models.enums import IndicatorKey, IndicatorSource
from tests.conftest import post_checkin as _post_checkin
from tests.conftest import register_and_login as _register_and_login
from tests.conftest import user_id as _user_id

OWNER_EMAIL = "deviation@example.com"
OWNER_PASSWORD = "senhaForte123"


def test_run_all_engines_with_no_data_returns_nothing(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post("/api/v1/deviation/run", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_stability_engine_requires_minimum_baseline_sample(client):
    """2 check-ins não bastam pra confiar num baseline (MIN_BASELINE_SAMPLE=5),
    mesmo que os valores pareçam uma queda óbvia."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _post_checkin(client, headers, 2, mood=4)
    _post_checkin(client, headers, 1, mood=1)
    _post_checkin(client, headers, 0, mood=1)

    response = client.post("/api/v1/deviation/run/stability", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_stability_engine_detects_persistent_mood_drop(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    # 10 dias de humor estável (4), depois 3 dias seguidos de humor baixo (1)
    for days_ago in range(12, 2, -1):
        _post_checkin(client, headers, days_ago, mood=4)
    for days_ago in (2, 1, 0):
        _post_checkin(client, headers, days_ago, mood=1)

    response = client.post("/api/v1/deviation/run/stability", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body["engine"] == "stability"
    assert "mood" in body["triggering_indicator_keys"]
    assert body["duration_days"] >= 3
    assert body["domains_count"] >= 1
    assert "Sua rotina mudou" in body["explanation"]
    assert "mood" in body["baseline_snapshot"]


def test_stability_engine_gap_in_checkins_breaks_the_streak(client):
    """Indicador subjetivo (humor) não é de contagem: um dia sem
    check-in quebra a sequência, não conta como zero nem repete o
    valor anterior."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    for days_ago in range(12, 2, -1):
        _post_checkin(client, headers, days_ago, mood=4)
    _post_checkin(client, headers, 2, mood=1)
    # dia 1 sem check-in nenhum (buraco)
    _post_checkin(client, headers, 0, mood=1)

    response = client.post("/api/v1/deviation/run/stability", headers=headers)
    assert response.status_code == 200
    # a sequência a partir do dia mais recente (hoje) já quebra no dia
    # seguinte (buraco), então nunca atinge MIN_DURATION_DAYS=3
    assert response.json() is None


def test_avoidance_engine_detects_persistent_anxiety_increase(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    for days_ago in range(12, 2, -1):
        _post_checkin(client, headers, days_ago, anxiety=2)
    for days_ago in (2, 1, 0):
        _post_checkin(client, headers, days_ago, anxiety=5)

    response = client.post("/api/v1/deviation/run/avoidance", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body["engine"] == "avoidance"
    assert "anxiety" in body["triggering_indicator_keys"]


def test_activation_engine_detects_persistent_energy_drop(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    for days_ago in range(12, 2, -1):
        _post_checkin(client, headers, days_ago, energy=4)
    for days_ago in (2, 1, 0):
        _post_checkin(client, headers, days_ago, energy=1)

    response = client.post("/api/v1/deviation/run/activation", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body["engine"] == "activation"
    assert "energy" in body["triggering_indicator_keys"]


def test_executive_engine_treats_missing_days_as_zero_for_count_indicator(client, db_session):
    """
    Indicador de contagem (tarefas concluídas): dias sem nenhum
    FunctionalIndicator registrado contam como zero de verdade, não
    como buraco — ausência de evento de tarefa É zero atividade.
    Escreve direto em FunctionalIndicator (o motor só lê essa tabela,
    nunca TaskEvent) pra simular histórico sem depender de
    TaskEvent.occurred_at, que é sempre definido pelo servidor.
    """
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    user_id = _user_id(db_session, OWNER_EMAIL)

    # histórico estável (7 dias, valores variando pra ter desvio padrão != 0)
    for offset in range(5, 12):
        day = datetime.date.today() - datetime.timedelta(days=offset)
        value = 3.0 if offset % 2 == 0 else 4.0
        db_session.add(
            FunctionalIndicator(
                user_id=user_id,
                indicator_key=IndicatorKey.TASKS_COMPLETED_COUNT,
                source=IndicatorSource.TASK_EVENT,
                value=value,
                recorded_for_date=day,
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )
        )
    db_session.commit()
    # dias 0-4 (hoje e os 4 anteriores): nenhuma tarefa concluída, sem
    # nenhum registro em FunctionalIndicator — zero-fill deve pegar isso.

    response = client.post("/api/v1/deviation/run/executive", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body["engine"] == "executive"
    assert "tasks_completed_count" in body["triggering_indicator_keys"]
    assert body["duration_days"] >= 3


def test_run_all_engines_returns_only_triggered_ones(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    for days_ago in range(12, 2, -1):
        _post_checkin(client, headers, days_ago, mood=4, anxiety=2)
    for days_ago in (2, 1, 0):
        _post_checkin(client, headers, days_ago, mood=1, anxiety=2)

    events = client.post("/api/v1/deviation/run", headers=headers).json()
    engines = {e["engine"] for e in events}
    assert "stability" in engines
    assert "avoidance" not in engines  # ansiedade nunca mudou


def test_deviation_events_are_listed_and_readable_by_id(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    for days_ago in range(12, 2, -1):
        _post_checkin(client, headers, days_ago, mood=4)
    for days_ago in (2, 1, 0):
        _post_checkin(client, headers, days_ago, mood=1)
    client.post("/api/v1/deviation/run/stability", headers=headers)

    listing = client.get("/api/v1/deviation/events", headers=headers).json()
    assert len(listing) == 1
    event_id = listing[0]["id"]

    fetched = client.get(f"/api/v1/deviation/events/{event_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == event_id

    filtered = client.get("/api/v1/deviation/events?engine=stability", headers=headers).json()
    assert len(filtered) == 1
    filtered_out = client.get("/api/v1/deviation/events?engine=avoidance", headers=headers).json()
    assert filtered_out == []


def test_deviation_events_are_private_to_their_owner(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    for days_ago in range(12, 2, -1):
        _post_checkin(client, owner_headers, days_ago, mood=4)
    for days_ago in (2, 1, 0):
        _post_checkin(client, owner_headers, days_ago, mood=1)
    client.post("/api/v1/deviation/run/stability", headers=owner_headers)
    event_id = client.get("/api/v1/deviation/events", headers=owner_headers).json()[0]["id"]

    other_headers = _register_and_login(client, "outro-deviation@example.com", "outraSenhaForte123")
    assert client.get("/api/v1/deviation/events", headers=other_headers).json() == []
    assert client.get(f"/api/v1/deviation/events/{event_id}", headers=other_headers).status_code == 404
