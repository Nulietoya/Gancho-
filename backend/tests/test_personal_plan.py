"""
ETAPA 25 (item 19) — plano pessoal ("plano quando eu não perceber").
Cobre o ciclo de vida do dono (criar/ler/editar/desativar plano,
adicionar/editar regra, unicidade de plano ativo, isolamento entre
usuários) e o acesso da pessoa de confiança via ACCESS_CRISIS_PLAN.
"""
from app.models.trust import TrustedPersonRelationship
from tests.conftest import register_and_login as _register_and_login

OWNER_EMAIL = "plano-dono@example.com"
OWNER_PASSWORD = "senhaForte123"
TRUSTED_EMAIL = "plano-confianca@example.com"
TRUSTED_PASSWORD = "outraSenhaForte123"


def _fully_connected_relationship(client, db_session):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/trusted-people/invite", json={"email": TRUSTED_EMAIL}, headers=owner_headers)
    raw_token = (
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one().invite_token
    )
    trusted_headers = _register_and_login(client, TRUSTED_EMAIL, TRUSTED_PASSWORD)
    client.post("/api/v1/trusted-people/accept", json={"invite_token": raw_token}, headers=trusted_headers)
    relationship_id = str(
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one().id
    )
    return owner_headers, trusted_headers, relationship_id


# --- CRUD do dono -----------------------------------------------------------


def test_get_plan_404_when_none_exists(client):
    headers = _register_and_login(client, "plano-vazio@example.com", "senhaForte123")
    response = client.get("/api/v1/personal-plan", headers=headers)
    assert response.status_code == 404


def test_create_and_get_plan(client):
    headers = _register_and_login(client, "plano-criar@example.com", "senhaForte123")
    create = client.post(
        "/api/v1/personal-plan",
        json={"title": "Meu plano", "description": "O que fazer se eu sumir por 3 dias"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["title"] == "Meu plano"
    assert body["is_active"] is True
    assert body["rules"] == []

    got = client.get("/api/v1/personal-plan", headers=headers).json()
    assert got["id"] == body["id"]


def test_create_plan_twice_conflicts(client):
    headers = _register_and_login(client, "plano-duplo@example.com", "senhaForte123")
    client.post(
        "/api/v1/personal-plan", json={"title": "Plano A", "description": "desc"}, headers=headers
    )
    second = client.post(
        "/api/v1/personal-plan", json={"title": "Plano B", "description": "desc"}, headers=headers
    )
    assert second.status_code == 409


def test_update_plan(client):
    headers = _register_and_login(client, "plano-editar@example.com", "senhaForte123")
    client.post(
        "/api/v1/personal-plan", json={"title": "Original", "description": "desc original"}, headers=headers
    )
    patched = client.patch(
        "/api/v1/personal-plan", json={"description": "desc nova"}, headers=headers
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["title"] == "Original"
    assert body["description"] == "desc nova"


def test_update_plan_404_when_none_exists(client):
    headers = _register_and_login(client, "plano-editar-vazio@example.com", "senhaForte123")
    response = client.patch("/api/v1/personal-plan", json={"description": "x"}, headers=headers)
    assert response.status_code == 404


def test_deactivate_plan_is_idempotent_and_allows_recreation(client):
    headers = _register_and_login(client, "plano-desativar@example.com", "senhaForte123")
    client.post(
        "/api/v1/personal-plan", json={"title": "Plano", "description": "desc"}, headers=headers
    )
    first = client.post("/api/v1/personal-plan/deactivate", headers=headers)
    assert first.status_code == 200
    assert first.json()["is_active"] is False

    second = client.post("/api/v1/personal-plan/deactivate", headers=headers)
    assert second.status_code == 200
    assert second.json()["is_active"] is False

    # sem plano ativo, GET volta a 404
    assert client.get("/api/v1/personal-plan", headers=headers).status_code == 404

    # mas um novo pode ser criado
    recreated = client.post(
        "/api/v1/personal-plan", json={"title": "Plano novo", "description": "desc nova"}, headers=headers
    )
    assert recreated.status_code == 201


# --- regras ------------------------------------------------------------------


def test_add_and_update_rule(client):
    headers = _register_and_login(client, "plano-regra@example.com", "senhaForte123")
    client.post(
        "/api/v1/personal-plan", json={"title": "Plano", "description": "desc"}, headers=headers
    )
    rule = client.post(
        "/api/v1/personal-plan/rules",
        json={"signal_key": "faltas", "threshold_description": "faltei 2 dias seguidos ao trabalho"},
        headers=headers,
    )
    assert rule.status_code == 201, rule.text
    rule_body = rule.json()
    assert rule_body["signal_key"] == "faltas"
    assert rule_body["is_active"] is True

    updated = client.patch(
        f"/api/v1/personal-plan/rules/{rule_body['id']}",
        json={"threshold_description": "faltei 3 dias seguidos", "is_active": False},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["threshold_description"] == "faltei 3 dias seguidos"
    assert updated.json()["is_active"] is False

    plan = client.get("/api/v1/personal-plan", headers=headers).json()
    assert len(plan["rules"]) == 1


def test_add_rule_404_when_no_active_plan(client):
    headers = _register_and_login(client, "plano-regra-vazio@example.com", "senhaForte123")
    response = client.post(
        "/api/v1/personal-plan/rules",
        json={"signal_key": "sono", "threshold_description": "durmo o dia todo"},
        headers=headers,
    )
    assert response.status_code == 404


def test_update_rule_404_for_other_users_rule(client):
    headers_a = _register_and_login(client, "plano-regra-a@example.com", "senhaForte123")
    headers_b = _register_and_login(client, "plano-regra-b@example.com", "senhaForte123")
    client.post("/api/v1/personal-plan", json={"title": "A", "description": "desc"}, headers=headers_a)
    rule = client.post(
        "/api/v1/personal-plan/rules",
        json={"signal_key": "isolamento", "threshold_description": "não saio de casa há 4 dias"},
        headers=headers_a,
    ).json()

    client.post("/api/v1/personal-plan", json={"title": "B", "description": "desc"}, headers=headers_b)
    cross = client.patch(
        f"/api/v1/personal-plan/rules/{rule['id']}",
        json={"is_active": False},
        headers=headers_b,
    )
    assert cross.status_code == 404


# --- acesso da pessoa de confiança (ACCESS_CRISIS_PLAN) ----------------------


def test_trusted_person_without_permission_gets_403(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    client.post(
        "/api/v1/personal-plan", json={"title": "Plano", "description": "desc"}, headers=owner_headers
    )
    response = client.get(f"/api/v1/trusted-people/{relationship_id}/personal-plan", headers=trusted_headers)
    assert response.status_code == 403


def test_trusted_person_with_permission_sees_plan(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    client.post(
        "/api/v1/personal-plan",
        json={"title": "Plano de crise", "description": "ligar pra minha irmã"},
        headers=owner_headers,
    )
    grant = client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": "access_crisis_plan", "is_granted": True}]},
        headers=owner_headers,
    )
    assert grant.status_code == 200, grant.text

    response = client.get(f"/api/v1/trusted-people/{relationship_id}/personal-plan", headers=trusted_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Plano de crise"


def test_trusted_person_with_permission_gets_404_when_owner_has_no_plan(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": "access_crisis_plan", "is_granted": True}]},
        headers=owner_headers,
    )
    response = client.get(f"/api/v1/trusted-people/{relationship_id}/personal-plan", headers=trusted_headers)
    assert response.status_code == 404
