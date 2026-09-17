"""
ETAPA 13 — medicamentos e adesão (item 13, o mais sensível até aqui).
Cobre: CRUD básico, descontinuação idempotente, horários aninhados a
um medicamento, e o registro de adesão em si — nunca uma
recomendação de dose, só o fato e o motivo quando não foi tomado.
"""
from tests.conftest import register_and_login as _register_and_login

OWNER_EMAIL = "medicacao@example.com"
OWNER_PASSWORD = "senhaForte123"


def _create_medication(client, headers, name="sertralina"):
    return client.post("/api/v1/medications", json={"name": name}, headers=headers).json()


def test_create_and_list_medication(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    assert med["discontinued_at"] is None

    listing = client.get("/api/v1/medications", headers=headers).json()
    assert len(listing) == 1


def test_discontinue_is_idempotent_and_hides_from_default_listing(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)

    first = client.post(f"/api/v1/medications/{med['id']}/discontinue", headers=headers)
    assert first.status_code == 200
    discontinued_at = first.json()["discontinued_at"]
    assert discontinued_at is not None

    second = client.post(f"/api/v1/medications/{med['id']}/discontinue", headers=headers)
    assert second.json()["discontinued_at"] == discontinued_at

    assert client.get("/api/v1/medications", headers=headers).json() == []
    with_discontinued = client.get("/api/v1/medications?include_discontinued=true", headers=headers).json()
    assert len(with_discontinued) == 1


def test_patch_updates_descriptive_fields(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    response = client.patch(f"/api/v1/medications/{med['id']}", json={"reminder_enabled": False}, headers=headers)
    assert response.status_code == 200
    assert response.json()["reminder_enabled"] is False
    assert response.json()["name"] == "sertralina"


def test_create_schedule_for_medication(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    response = client.post(
        f"/api/v1/medications/{med['id']}/schedules",
        json={"time_of_day": "08:00:00", "weekdays": [0, 1, 2, 3, 4]},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["time_of_day"] == "08:00:00"
    assert body["weekdays"] == [0, 1, 2, 3, 4]


def test_update_schedule_changes_time_of_day(client):
    """
    ETAPA 33-34: achado via `pytest --cov` — `update_schedule`
    (medication_service.py) nunca tinha sido exercitado no caminho de
    sucesso, só o 404 de posse. Rota real (editar o horário de uma
    dose já cadastrada), sem teste nenhum até aqui.
    """
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    schedule = _create_schedule(client, headers, med["id"], time_of_day="08:00:00")

    response = client.patch(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}",
        json={"time_of_day": "09:30:00"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["time_of_day"] == "09:30:00"


def test_list_events_for_a_single_schedule_excludes_other_schedules_of_the_same_medication(client):
    """
    ETAPA 33-34: achado via `pytest --cov` — `list_events_for_schedule`
    nunca tinha sido chamado por nenhum teste (só
    `list_events_for_medication`, a versão "todas as doses juntas").
    Cobre também que ela filtra por `schedule_id`, não só por
    `medication_id` — comportamento diferente do endpoint irmão.
    """
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    morning = _create_schedule(client, headers, med["id"], "08:00:00")
    night = _create_schedule(client, headers, med["id"], "22:00:00")

    client.post(
        f"/api/v1/medications/{med['id']}/schedules/{morning['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "taken"},
        headers=headers,
    )
    client.post(
        f"/api/v1/medications/{med['id']}/schedules/{night['id']}/events",
        json={"scheduled_for": "2026-09-12T22:00:00Z", "status": "taken"},
        headers=headers,
    )

    morning_events = client.get(
        f"/api/v1/medications/{med['id']}/schedules/{morning['id']}/events", headers=headers
    ).json()
    assert len(morning_events) == 1
    assert morning_events[0]["schedule_id"] == morning["id"]


def test_list_schedules_returns_every_schedule_of_the_medication(client):
    """ETAPA 33-34: achado via `pytest --cov` — `list_schedules` só tinha teste do 404 de posse, nunca do conteúdo em si."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    _create_schedule(client, headers, med["id"], "08:00:00")
    _create_schedule(client, headers, med["id"], "22:00:00")

    schedules = client.get(f"/api/v1/medications/{med['id']}/schedules", headers=headers).json()
    assert sorted(s["time_of_day"] for s in schedules) == ["08:00:00", "22:00:00"]


def test_schedule_rejects_invalid_weekday(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    response = client.post(
        f"/api/v1/medications/{med['id']}/schedules",
        json={"time_of_day": "08:00:00", "weekdays": [0, 7]},
        headers=headers,
    )
    assert response.status_code == 422


def _create_schedule(client, headers, medication_id, time_of_day="08:00:00"):
    return client.post(
        f"/api/v1/medications/{medication_id}/schedules",
        json={"time_of_day": time_of_day},
        headers=headers,
    ).json()


def test_taken_event_needs_no_reason(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    schedule = _create_schedule(client, headers, med["id"])

    response = client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "taken"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["skip_reason"] is None


def test_non_taken_event_requires_reason(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    schedule = _create_schedule(client, headers, med["id"])

    missing_reason = client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "not_taken"},
        headers=headers,
    )
    assert missing_reason.status_code == 422

    with_reason = client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "not_taken", "skip_reason": "esqueci"},
        headers=headers,
    )
    assert with_reason.status_code == 201
    assert with_reason.json()["skip_reason"] == "esqueci"


def test_forgot_to_confirm_cannot_be_set_by_the_user(client):
    """Reservado pro job automático futuro (ETAPA 22) — a pessoa não escolhe esse status."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    schedule = _create_schedule(client, headers, med["id"])

    response = client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={
            "scheduled_for": "2026-09-12T08:00:00Z",
            "status": "forgot_to_confirm",
            "skip_reason": "esqueci",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_adherence_tip_absent_on_first_occurrence_of_a_reason(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    schedule = _create_schedule(client, headers, med["id"])

    response = client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "not_taken", "skip_reason": "esqueci"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["adherence_tip"] is None


def test_adherence_tip_appears_when_the_same_reason_repeats(client):
    """Pedido do usuário: motivo repetido vira dica concreta, não só mais um registro igual."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    schedule = _create_schedule(client, headers, med["id"])

    client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "not_taken", "skip_reason": "esqueci"},
        headers=headers,
    )
    second = client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": "2026-09-13T08:00:00Z", "status": "not_taken", "skip_reason": "esqueci"},
        headers=headers,
    )
    assert second.status_code == 201
    tip = second.json()["adherence_tip"]
    assert tip is not None
    assert "hábito" in tip.lower()


def test_adherence_tip_counts_across_schedules_of_the_same_medication(client):
    """Esquecer a dose da manhã e a da noite pelo mesmo motivo é o mesmo padrão."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    morning = _create_schedule(client, headers, med["id"], "08:00:00")
    night = _create_schedule(client, headers, med["id"], "22:00:00")

    client.post(
        f"/api/v1/medications/{med['id']}/schedules/{morning['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "not_taken", "skip_reason": "rotina_mudou"},
        headers=headers,
    )
    second = client.post(
        f"/api/v1/medications/{med['id']}/schedules/{night['id']}/events",
        json={"scheduled_for": "2026-09-12T22:00:00Z", "status": "not_taken", "skip_reason": "rotina_mudou"},
        headers=headers,
    )
    assert second.json()["adherence_tip"] is not None


def test_adherence_tip_never_appears_for_own_decision(client):
    """DECISAO_PROPRIA fica sem dica de propósito — não questiona uma decisão informada."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    schedule = _create_schedule(client, headers, med["id"])

    client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "skipped_deliberately", "skip_reason": "decisao_propria"},
        headers=headers,
    )
    second = client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": "2026-09-13T08:00:00Z", "status": "skipped_deliberately", "skip_reason": "decisao_propria"},
        headers=headers,
    )
    assert second.json()["adherence_tip"] is None


def test_adherence_tip_never_shown_on_plain_listing(client):
    """A dica é um nudge no momento do registro, não um rótulo permanente no histórico."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    schedule = _create_schedule(client, headers, med["id"])

    for scheduled_for in ("2026-09-12T08:00:00Z", "2026-09-13T08:00:00Z"):
        client.post(
            f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
            json={"scheduled_for": scheduled_for, "status": "not_taken", "skip_reason": "esqueci"},
            headers=headers,
        )

    events = client.get(f"/api/v1/medications/{med['id']}/events", headers=headers).json()
    assert len(events) == 2
    assert all(e["adherence_tip"] is None for e in events)


def test_events_are_listed_across_schedules_of_the_same_medication(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, headers)
    morning = _create_schedule(client, headers, med["id"], "08:00:00")
    night = _create_schedule(client, headers, med["id"], "22:00:00")

    client.post(
        f"/api/v1/medications/{med['id']}/schedules/{morning['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "taken"},
        headers=headers,
    )
    client.post(
        f"/api/v1/medications/{med['id']}/schedules/{night['id']}/events",
        json={"scheduled_for": "2026-09-12T22:00:00Z", "status": "skipped_deliberately", "skip_reason": "decisao_propria"},
        headers=headers,
    )

    events = client.get(f"/api/v1/medications/{med['id']}/events", headers=headers).json()
    assert len(events) == 2


def test_medications_and_schedules_are_private_to_their_owner(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, owner_headers)
    schedule = _create_schedule(client, owner_headers, med["id"])

    other_headers = _register_and_login(client, "outra-medicacao@example.com", "outraSenhaForte123")
    assert client.get(f"/api/v1/medications/{med['id']}", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/medications/{med['id']}/schedules", headers=other_headers).status_code == 404
    response = client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "taken"},
        headers=other_headers,
    )
    assert response.status_code == 404


def test_every_mutating_medication_route_404s_for_a_medication_that_belongs_to_someone_else(client):
    """
    ETAPA 33-34: o teste acima só cobria 3 das 8 rotas que checam posse
    — cada uma tem seu próprio `except MedicationNotFound` em
    `app/api/v1/medications.py` (achado rodando `pytest --cov`, ver
    `docs/decisions.md`). Mesmo raciocínio de segurança do teste
    equivalente em tarefas: precisa ser 404 em toda rota, nunca um
    engano silencioso numa rota adicionada depois.
    """
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med = _create_medication(client, owner_headers)
    schedule = _create_schedule(client, owner_headers, med["id"])

    other_headers = _register_and_login(client, "outra-medicacao-2@example.com", "outraSenhaForte123")

    assert client.patch(f"/api/v1/medications/{med['id']}", json={"name": "x"}, headers=other_headers).status_code == 404
    assert client.post(f"/api/v1/medications/{med['id']}/discontinue", headers=other_headers).status_code == 404
    assert (
        client.post(
            f"/api/v1/medications/{med['id']}/schedules",
            json={"time_of_day": "09:00:00"},
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}",
            json={"time_of_day": "10:00:00"},
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events", headers=other_headers
        ).status_code
        == 404
    )
    assert client.get(f"/api/v1/medications/{med['id']}/events", headers=other_headers).status_code == 404


def test_schedule_id_from_a_different_medication_404s_as_schedule_not_found(client):
    """
    `get_schedule` (medication_service.py) exige que `schedule_id`
    pertença ao `medication_id` da própria URL, não só que ambos
    existam e sejam do mesmo usuário — `ScheduleNotFound`, caminho
    nunca exercitado por nenhum teste até esta etapa (achado via
    `pytest --cov`: `_schedule_not_found()` aparecia como linha morta
    em `app/api/v1/medications.py`). Cobre `update_schedule`,
    `create_event` e `list_events_for_schedule` — as três rotas que
    distinguem `MedicationNotFound` de `ScheduleNotFound`.
    """
    headers = _register_and_login(client, "duas-medicacoes@example.com", "senhaForte123")
    med_a = _create_medication(client, headers, name="sertralina")
    med_b = _create_medication(client, headers, name="bupropiona")
    schedule_of_a = _create_schedule(client, headers, med_a["id"])

    assert (
        client.patch(
            f"/api/v1/medications/{med_b['id']}/schedules/{schedule_of_a['id']}",
            json={"time_of_day": "10:00:00"},
            headers=headers,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/medications/{med_b['id']}/schedules/{schedule_of_a['id']}/events",
            json={"scheduled_for": "2026-09-12T08:00:00Z", "status": "taken"},
            headers=headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/medications/{med_b['id']}/schedules/{schedule_of_a['id']}/events", headers=headers
        ).status_code
        == 404
    )
