"""
ETAPA 10 — tarefas e eventos de tarefa (itens 7/8/9/24/25/33). Cobre a
máquina de estados (o que pode transicionar pra onde), o motivo de
não-conclusão sendo obrigatório ao adiar, o histórico de eventos como
fonte de verdade, e a sugestão de tarefa por pessoa de confiança
gated pela permissão certa (mesmo padrão da ETAPA 7/14/16).
"""
from tests.conftest import register_and_login as _register_and_login

OWNER_EMAIL = "tarefas@example.com"
OWNER_PASSWORD = "senhaForte123"
TRUSTED_EMAIL = "apoio@example.com"
TRUSTED_PASSWORD = "outraSenhaForte123"


def _create_task(client, headers, title="lavar louça"):
    return client.post("/api/v1/tasks", json={"title": title}, headers=headers).json()


def test_create_task_starts_pending_and_logs_created_event(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, headers)
    assert task["status"] == "pending"
    assert task["postponed_count"] == 0
    assert task["attempt_count"] == 0

    events = client.get(f"/api/v1/tasks/{task['id']}/events", headers=headers).json()
    assert len(events) == 1
    assert events[0]["event_type"] == "created"


def test_start_task_sets_started_at_and_increments_attempt_count(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, headers)

    response = client.post(f"/api/v1/tasks/{task['id']}/start", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "started"
    assert body["started_at"] is not None
    assert body["attempt_count"] == 1


def test_cannot_start_an_already_completed_task(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, headers)
    client.post(f"/api/v1/tasks/{task['id']}/complete", headers=headers)

    response = client.post(f"/api/v1/tasks/{task['id']}/start", headers=headers)
    assert response.status_code == 409


def test_postpone_requires_a_reason_and_increments_counter(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, headers)

    missing_reason = client.post(f"/api/v1/tasks/{task['id']}/postpone", json={}, headers=headers)
    assert missing_reason.status_code == 422

    response = client.post(
        f"/api/v1/tasks/{task['id']}/postpone",
        json={"reason": "nao_consegui_comecar"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "postponed"
    assert body["postponed_count"] == 1


def test_postponed_task_can_be_started_again(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, headers)
    client.post(f"/api/v1/tasks/{task['id']}/postpone", json={"reason": "me_distrai"}, headers=headers)

    response = client.post(f"/api/v1/tasks/{task['id']}/start", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_full_lifecycle_pause_resume_complete(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, headers)

    client.post(f"/api/v1/tasks/{task['id']}/start", headers=headers)
    paused = client.post(f"/api/v1/tasks/{task['id']}/pause", headers=headers)
    assert paused.json()["status"] == "paused"

    resumed = client.post(f"/api/v1/tasks/{task['id']}/resume", headers=headers)
    assert resumed.json()["status"] == "started"
    assert resumed.json()["attempt_count"] == 2  # start + resume

    completed = client.post(f"/api/v1/tasks/{task['id']}/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"] is not None

    events = client.get(f"/api/v1/tasks/{task['id']}/events", headers=headers).json()
    assert [e["event_type"] for e in events] == ["created", "started", "paused", "resumed", "completed"]


def test_cancel_without_reason_is_allowed(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, headers)
    response = client.post(f"/api/v1/tasks/{task['id']}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_patch_updates_descriptive_fields_but_never_status(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, headers)
    response = client.patch(f"/api/v1/tasks/{task['id']}", json={"title": "lavar louça e secar"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "lavar louça e secar"
    assert response.json()["status"] == "pending"


def test_tasks_are_private_to_their_owner(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, owner_headers)

    other_headers = _register_and_login(client, "outra-pessoa@example.com", "outraSenhaForte123")
    response = client.get(f"/api/v1/tasks/{task['id']}", headers=other_headers)
    assert response.status_code == 404

    listing = client.get("/api/v1/tasks", headers=other_headers).json()
    assert listing == []


def test_every_mutating_task_route_404s_for_a_task_that_belongs_to_someone_else(client):
    """
    ETAPA 33-34: `test_tasks_are_private_to_their_owner` só cobria
    `GET /tasks/{id}` — cada rota de transição/mutação tem seu próprio
    bloco `except TaskNotFound: raise _not_found()` em
    `app/api/v1/tasks.py`, e nenhum deles tinha teste próprio (achado
    rodando `pytest --cov`, ver `docs/decisions.md`). O comportamento
    é de segurança, não só de UX: uma tarefa de outra pessoa precisa
    responder 404 em toda rota, nunca vazar a existência dela através
    de um 409 ("estado inválido") ou 500 por engano de algum `except`
    esquecido numa rota nova.
    """
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, owner_headers)
    task_id = task["id"]

    other_headers = _register_and_login(client, "outra-pessoa-tarefas@example.com", "outraSenhaForte123")

    assert client.patch(f"/api/v1/tasks/{task_id}", json={"title": "x"}, headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/tasks/{task_id}/events", headers=other_headers).status_code == 404
    assert client.post(f"/api/v1/tasks/{task_id}/start", headers=other_headers).status_code == 404
    assert client.post(f"/api/v1/tasks/{task_id}/pause", headers=other_headers).status_code == 404
    assert client.post(f"/api/v1/tasks/{task_id}/resume", headers=other_headers).status_code == 404
    assert (
        client.post(
            f"/api/v1/tasks/{task_id}/postpone", json={"reason": "nao_consegui_comecar"}, headers=other_headers
        ).status_code
        == 404
    )
    assert client.post(f"/api/v1/tasks/{task_id}/complete", headers=other_headers).status_code == 404
    assert client.post(f"/api/v1/tasks/{task_id}/cancel", headers=other_headers).status_code == 404


def _accepted_relationship_with_permission(client, db_session, permission_key="suggest_task"):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/trusted-people/invite", json={"email": TRUSTED_EMAIL}, headers=owner_headers)

    from app.models.trust import TrustedPersonRelationship

    raw_token = (
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one().invite_token
    )
    trusted_headers = _register_and_login(client, TRUSTED_EMAIL, TRUSTED_PASSWORD)
    client.post("/api/v1/trusted-people/accept", json={"invite_token": raw_token}, headers=trusted_headers)

    relationship_id = (
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one().id
    )
    client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": permission_key, "is_granted": True}]},
        headers=owner_headers,
    )
    return owner_headers, trusted_headers, str(relationship_id)


def test_trusted_person_with_suggest_task_permission_can_suggest_task_for_owner(client, db_session):
    owner_headers, trusted_headers, relationship_id = _accepted_relationship_with_permission(client, db_session)

    response = client.post(
        f"/api/v1/trusted-people/{relationship_id}/tasks/suggest",
        json={"title": "tomar um copo d'água"},
        headers=trusted_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["origin"] == "trusted_person_suggestion"
    assert body["source_relationship_id"] == relationship_id

    owner_tasks = client.get("/api/v1/tasks", headers=owner_headers).json()
    assert any(t["id"] == body["id"] for t in owner_tasks)


def test_trusted_person_without_suggest_task_permission_cannot_suggest_task(client, db_session):
    """Ter RECORD_OBSERVATION concedida não dá acesso a sugerir tarefa (item 45/70)."""
    owner_headers, trusted_headers, relationship_id = _accepted_relationship_with_permission(
        client, db_session, permission_key="record_observation"
    )

    response = client.post(
        f"/api/v1/trusted-people/{relationship_id}/tasks/suggest",
        json={"title": "tomar um copo d'água"},
        headers=trusted_headers,
    )
    assert response.status_code == 403
