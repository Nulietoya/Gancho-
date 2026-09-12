"""
ETAPA 21 — intervenções (microintervenção / body doubling). Cobre a
sugestão (com validação de posse de tarefa/evento de desvio
relacionados e rotação do catálogo), a máquina de estados (incluindo
o atalho de baixo atrito SUGGESTED -> STARTED e `dismiss` de qualquer
estado não-terminal), o registro de resultado só depois de FINISHED,
e o fluxo completo de body doubling terminando no primeiro uso real
de HELP_WITH_TASK pela pessoa de confiança.
"""
from app.models.trust import TrustedPersonRelationship
from tests.conftest import register_and_login as _register_and_login

OWNER_EMAIL = "intervencoes@example.com"
OWNER_PASSWORD = "senhaForte123"
TRUSTED_EMAIL = "apoio-intervencoes@example.com"
TRUSTED_PASSWORD = "outraSenhaForte123"
STRANGER_EMAIL = "estranho-intervencoes@example.com"
STRANGER_PASSWORD = "maisUmaSenha123"


def _create_task(client, headers):
    response = client.post(
        "/api/v1/tasks", json={"title": "lavar a louça", "priority": "medium"}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def _fully_connected_relationship(client, db_session):
    """Convite aceito entre dono e pessoa de confiança, sem permissão concedida ainda."""
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/trusted-people/invite", json={"email": TRUSTED_EMAIL}, headers=owner_headers)

    raw_token = (
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one().invite_token
    )
    trusted_headers = _register_and_login(client, TRUSTED_EMAIL, TRUSTED_PASSWORD)
    client.post("/api/v1/trusted-people/accept", json={"invite_token": raw_token}, headers=trusted_headers)

    relationship_id = (
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one().id
    )
    return owner_headers, trusted_headers, str(relationship_id)


def _grant_help_with_task(client, owner_headers, relationship_id):
    response = client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": "help_with_task", "is_granted": True}]},
        headers=owner_headers,
    )
    assert response.status_code == 200, response.text


def test_suggest_microintervention_defaults_and_rotates_catalog(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    first = client.post("/api/v1/interventions/suggest", json={}, headers=headers)
    assert first.status_code == 201
    body = first.json()
    assert body["type"] == "microintervention"
    assert body["status"] == "suggested"
    assert body["support_relationship_id"] is None

    second = client.post("/api/v1/interventions/suggest", json={}, headers=headers)
    assert second.json()["suggestion_text"] != body["suggestion_text"]


def test_suggest_body_doubling_uses_fixed_text(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post(
        "/api/v1/interventions/suggest", json={"type": "body_doubling_session"}, headers=headers
    )
    assert response.status_code == 201
    assert "por perto" in response.json()["suggestion_text"]


def test_suggest_with_related_task_validates_ownership(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    task = _create_task(client, owner_headers)

    ok = client.post(
        "/api/v1/interventions/suggest",
        json={"related_task_id": task["id"]},
        headers=owner_headers,
    )
    assert ok.status_code == 201
    assert ok.json()["related_task_id"] == task["id"]

    stranger_headers = _register_and_login(client, STRANGER_EMAIL, STRANGER_PASSWORD)
    blocked = client.post(
        "/api/v1/interventions/suggest",
        json={"related_task_id": task["id"]},
        headers=stranger_headers,
    )
    assert blocked.status_code == 404


def test_suggest_with_unknown_deviation_event_is_404(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(
        "/api/v1/interventions/suggest",
        json={"related_deviation_id": fake_id},
        headers=headers,
    )
    assert response.status_code == 404


def test_microintervention_can_start_directly_from_suggested(client):
    """Item 17: friction mínima — não precisa pedir/aceitar pra começar sozinho."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    intervention = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()

    start = client.post(f"/api/v1/interventions/{intervention['id']}/start", headers=headers)
    assert start.status_code == 200
    assert start.json()["status"] == "started"

    finish = client.post(f"/api/v1/interventions/{intervention['id']}/finish", headers=headers)
    assert finish.status_code == 200
    assert finish.json()["status"] == "finished"


def test_invalid_transition_returns_409(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    intervention = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()

    response = client.post(f"/api/v1/interventions/{intervention['id']}/finish", headers=headers)
    assert response.status_code == 409


def test_dismiss_allowed_from_any_nonterminal_state(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    suggested = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    dismissed = client.post(f"/api/v1/interventions/{suggested['id']}/dismiss", headers=headers)
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"

    started = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    client.post(f"/api/v1/interventions/{started['id']}/start", headers=headers)
    dismissed_after_start = client.post(f"/api/v1/interventions/{started['id']}/dismiss", headers=headers)
    assert dismissed_after_start.status_code == 200

    # terminal: já dispensada não pode ser dispensada de novo
    again = client.post(f"/api/v1/interventions/{suggested['id']}/dismiss", headers=headers)
    assert again.status_code == 409


def test_record_result_only_after_finished(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    intervention = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()

    too_early = client.put(
        f"/api/v1/interventions/{intervention['id']}/result",
        json={"helped": True},
        headers=headers,
    )
    assert too_early.status_code == 409

    client.post(f"/api/v1/interventions/{intervention['id']}/start", headers=headers)
    client.post(f"/api/v1/interventions/{intervention['id']}/finish", headers=headers)

    result = client.put(
        f"/api/v1/interventions/{intervention['id']}/result",
        json={"helped": True, "user_note": "ajudou a começar"},
        headers=headers,
    )
    assert result.status_code == 200
    assert result.json()["helped"] is True


def test_record_result_upserts_instead_of_duplicating(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    intervention = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    client.post(f"/api/v1/interventions/{intervention['id']}/start", headers=headers)
    client.post(f"/api/v1/interventions/{intervention['id']}/finish", headers=headers)

    first = client.put(
        f"/api/v1/interventions/{intervention['id']}/result", json={"helped": False}, headers=headers
    ).json()
    second = client.put(
        f"/api/v1/interventions/{intervention['id']}/result",
        json={"helped": True, "user_note": "na verdade ajudou"},
        headers=headers,
    ).json()
    assert first["id"] == second["id"]
    assert second["helped"] is True


def test_body_doubling_full_flow_with_trusted_person_accept(client, db_session):
    """
    Item 24 — primeiro uso real de HELP_WITH_TASK: o dono pede body
    doubling endereçado a uma pessoa de confiança específica, ela
    aceita, o dono inicia e finaliza a sessão e registra o resultado.
    """
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    _grant_help_with_task(client, owner_headers, relationship_id)

    suggestion = client.post(
        "/api/v1/interventions/suggest", json={"type": "body_doubling_session"}, headers=owner_headers
    ).json()

    requested = client.post(
        f"/api/v1/interventions/{suggestion['id']}/request",
        json={"support_relationship_id": relationship_id},
        headers=owner_headers,
    )
    assert requested.status_code == 200
    assert requested.json()["status"] == "requested"
    assert requested.json()["support_relationship_id"] == relationship_id

    accepted = client.post(
        f"/api/v1/trusted-people/{relationship_id}/interventions/{suggestion['id']}/accept",
        headers=trusted_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    started = client.post(f"/api/v1/interventions/{suggestion['id']}/start", headers=owner_headers)
    assert started.json()["status"] == "started"
    finished = client.post(f"/api/v1/interventions/{suggestion['id']}/finish", headers=owner_headers)
    assert finished.json()["status"] == "finished"

    result = client.put(
        f"/api/v1/interventions/{suggestion['id']}/result", json={"helped": True}, headers=owner_headers
    )
    assert result.status_code == 200


def test_accept_without_permission_is_403(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    suggestion = client.post(
        "/api/v1/interventions/suggest", json={"type": "body_doubling_session"}, headers=owner_headers
    ).json()
    client.post(
        f"/api/v1/interventions/{suggestion['id']}/request",
        json={"support_relationship_id": relationship_id},
        headers=owner_headers,
    )

    response = client.post(
        f"/api/v1/trusted-people/{relationship_id}/interventions/{suggestion['id']}/accept",
        headers=trusted_headers,
    )
    assert response.status_code == 403


def test_accept_addressed_to_a_different_relationship_is_404(client, db_session):
    """
    Ter HELP_WITH_TASK concedida não dá acesso a aceitar QUALQUER
    pedido de body doubling — só o que foi endereçado a este
    relacionamento especificamente.
    """
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    _grant_help_with_task(client, owner_headers, relationship_id)

    # Sugestão nunca chega a ser "pedida" a ninguém (support_relationship_id fica None).
    suggestion = client.post(
        "/api/v1/interventions/suggest", json={"type": "body_doubling_session"}, headers=owner_headers
    ).json()

    response = client.post(
        f"/api/v1/trusted-people/{relationship_id}/interventions/{suggestion['id']}/accept",
        headers=trusted_headers,
    )
    assert response.status_code == 404


def test_interventions_are_private_to_their_owner(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    intervention = client.post("/api/v1/interventions/suggest", json={}, headers=owner_headers).json()

    stranger_headers = _register_and_login(client, STRANGER_EMAIL, STRANGER_PASSWORD)
    assert client.get("/api/v1/interventions", headers=stranger_headers).json() == []
    assert (
        client.get(f"/api/v1/interventions/{intervention['id']}", headers=stranger_headers).status_code
        == 404
    )
    assert (
        client.post(f"/api/v1/interventions/{intervention['id']}/start", headers=stranger_headers).status_code
        == 404
    )


def test_list_interventions_filters_by_status(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    kept_suggested = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    to_start = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    client.post(f"/api/v1/interventions/{to_start['id']}/start", headers=headers)

    suggested_only = client.get(
        "/api/v1/interventions", params={"status_filter": "suggested"}, headers=headers
    ).json()
    assert {i["id"] for i in suggested_only} == {kept_suggested["id"]}

    started_only = client.get(
        "/api/v1/interventions", params={"status_filter": "started"}, headers=headers
    ).json()
    assert {i["id"] for i in started_only} == {to_start["id"]}
