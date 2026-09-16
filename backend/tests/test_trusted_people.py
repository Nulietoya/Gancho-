"""
ETAPA 7 (autorização) + 14 (pessoas de confiança) + 16 (observações
externas). Os testes mais importantes aqui replicam, quase
literalmente, os cenários que o próprio documento de referência exige
nos itens 45/70/71: uma pessoa de confiança com uma permissão não
pode agir usando outra; alguém sem relação nenhuma não enxerga nem
que o relacionamento existe; revogar tira o acesso na hora, não
"na próxima renovação de token".
"""
from app.models import AuditLog
from app.models.enums import AuditAction, PermissionKey
from tests.conftest import register_and_login as _register_and_login

OWNER_EMAIL = "dono@example.com"
OWNER_PASSWORD = "senhaForte123"
TRUSTED_EMAIL = "confianca@example.com"
TRUSTED_PASSWORD = "outraSenhaForte123"
STRANGER_EMAIL = "estranho@example.com"
STRANGER_PASSWORD = "maisUmaSenha123"


def test_invite_creates_pending_relationship(client):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post(
        "/api/v1/trusted-people/invite",
        json={"email": TRUSTED_EMAIL, "relationship_label": "parceiro"},
        headers=owner_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["permissions"] == []


def test_invite_response_includes_token_and_list_reexposes_it_while_pending(client, db_session):
    """
    Regressão do bug real: o código do convite era gerado e gravado no
    banco, mas não saía dali — nem por e-mail, nem devolvido na
    resposta pra a pessoa dona copiar e mandar na mão. Confirma que a
    resposta do POST inclui o token de verdade (usável pra aceitar).

    Além disso, confirma a decisão mais recente: `GET /trusted-people`
    (só o dono vê a própria lista) volta a expor esse mesmo token
    ENQUANTO o convite está pendente — pra quem saiu da tela antes de
    copiar o link (ex.: o e-mail falhou) conseguir recuperá-lo depois,
    sem precisar cancelar e criar um convite novo. Depois de aceito, o
    link não serve mais pra nada, então o campo volta a ficar vazio.
    """
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post(
        "/api/v1/trusted-people/invite", json={"email": TRUSTED_EMAIL}, headers=owner_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert "invite_token" in body and body["invite_token"]

    from app.models.trust import TrustedPersonRelationship

    real_token = (
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one().invite_token
    )
    assert body["invite_token"] == real_token

    listed_pending = client.get("/api/v1/trusted-people", headers=owner_headers)
    assert listed_pending.status_code == 200
    assert listed_pending.json()[0]["invite_token"] == real_token

    trusted_headers = _register_and_login(client, TRUSTED_EMAIL, TRUSTED_PASSWORD)
    accept_response = client.post(
        "/api/v1/trusted-people/accept", json={"invite_token": real_token}, headers=trusted_headers
    )
    assert accept_response.status_code == 200

    listed_accepted = client.get("/api/v1/trusted-people", headers=owner_headers)
    assert listed_accepted.status_code == 200
    assert listed_accepted.json()[0]["invite_token"] is None


def test_watching_list_never_exposes_invite_token(client, db_session):
    """
    O campo novo só existe na resposta do DONO (`GET /trusted-people`).
    A pessoa de confiança vendo sua própria lista de quem observa
    (`GET /trusted-people/watching`) usa um schema diferente
    (`RelationshipAsTrustedPublic`) que nunca ganhou esse campo — o
    convite já foi aceito por ela mesma, então não haveria uso
    legítimo, e continua não sendo exposto por padrão.
    """
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    invite_response = client.post(
        "/api/v1/trusted-people/invite", json={"email": TRUSTED_EMAIL}, headers=owner_headers
    )
    raw_token = invite_response.json()["invite_token"]

    trusted_headers = _register_and_login(client, TRUSTED_EMAIL, TRUSTED_PASSWORD)
    client.post("/api/v1/trusted-people/accept", json={"invite_token": raw_token}, headers=trusted_headers)

    watching = client.get("/api/v1/trusted-people/watching", headers=trusted_headers)
    assert watching.status_code == 200
    assert "invite_token" not in watching.json()[0]


def test_accept_invite_rejects_wrong_email(client, db_session):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post(
        "/api/v1/trusted-people/invite", json={"email": TRUSTED_EMAIL}, headers=owner_headers
    )

    from app.models.trust import TrustedPersonRelationship

    relationship = db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one()
    raw_token = relationship.invite_token

    stranger_headers = _register_and_login(client, STRANGER_EMAIL, STRANGER_PASSWORD)
    response = client.post(
        "/api/v1/trusted-people/accept", json={"invite_token": raw_token}, headers=stranger_headers
    )
    assert response.status_code == 400


def test_accept_invite_activates_relationship(client, db_session):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/trusted-people/invite", json={"email": TRUSTED_EMAIL}, headers=owner_headers)

    from app.models.trust import TrustedPersonRelationship

    raw_token = (
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one().invite_token
    )
    trusted_headers = _register_and_login(client, TRUSTED_EMAIL, TRUSTED_PASSWORD)

    response = client.post(
        "/api/v1/trusted-people/accept", json={"invite_token": raw_token}, headers=trusted_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def _fully_connected_relationship(client, db_session):
    """Convite aceito, sem nenhuma permissão concedida ainda."""
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
    return owner_headers, trusted_headers, str(relationship_id)


def test_trusted_person_without_permission_cannot_record_observation(client, db_session):
    """Item 70: relação ativa, mas sem a permissão específica — 403."""
    _owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)

    response = client.post(
        f"/api/v1/trusted-people/{relationship_id}/observations",
        json={"category": "isolamento", "since": "hoje", "intensity": "leve"},
        headers=trusted_headers,
    )
    assert response.status_code == 403


def test_denied_observation_attempt_is_audited(client, db_session):
    """Item 31/54: toda tentativa negada de acesso a dado restrito é auditada."""
    _owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)

    client.post(
        f"/api/v1/trusted-people/{relationship_id}/observations",
        json={"category": "isolamento", "since": "hoje", "intensity": "leve"},
        headers=trusted_headers,
    )

    denied_logs = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == AuditAction.RESTRICTED_DATA_ACCESS_DENIED)
        .all()
    )
    # Filtra pelo relacionamento deste teste: o banco de dev pode ter logs
    # negados de execuções manuais anteriores (mesmo motivo do bug corrigido
    # nas queries de TrustedPersonRelationship acima).
    denied_logs = [
        log for log in denied_logs if log.log_metadata.get("relationship_id") == relationship_id
    ]
    assert len(denied_logs) == 1
    assert denied_logs[0].log_metadata["permission_key"] == PermissionKey.RECORD_OBSERVATION.value


def test_owner_can_grant_permission_and_trusted_person_can_then_act(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)

    grant = client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": "record_observation", "is_granted": True}]},
        headers=owner_headers,
    )
    assert grant.status_code == 200
    assert grant.json()["permissions"][0]["is_granted"] is True

    observe = client.post(
        f"/api/v1/trusted-people/{relationship_id}/observations",
        json={"category": "isolamento", "since": "hoje", "intensity": "leve", "note": "não saiu de casa"},
        headers=trusted_headers,
    )
    assert observe.status_code == 201


def test_granted_permission_does_not_leak_into_other_permissions(client, db_session):
    """
    Item 45/70 no ponto central: ter UMA permissão concedida não dá
    acesso a NENHUMA outra — nem a uma ação parecida.
    """
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": "record_observation", "is_granted": True}]},
        headers=owner_headers,
    )

    # RECORD_OBSERVATION concedida não implica nenhuma outra chave
    # estar concedida — o caso de revogação (uma permissão específica
    # deixando de valer) é coberto pelo teste de revogação abaixo.
    granted_keys = {
        p["permission_key"]
        for p in _owner_permissions(client, owner_headers, relationship_id)
        if p["is_granted"]
    }
    assert granted_keys == {"record_observation"}


def _owner_permissions(client, owner_headers, relationship_id):
    relationships = client.get("/api/v1/trusted-people", headers=owner_headers).json()
    match = next(r for r in relationships if r["id"] == relationship_id)
    return match["permissions"]


def test_revoking_relationship_immediately_blocks_further_observations(client, db_session):
    """Item 71: revogação vale na hora, sem depender de token expirar."""
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": "record_observation", "is_granted": True}]},
        headers=owner_headers,
    )
    assert (
        client.post(
            f"/api/v1/trusted-people/{relationship_id}/observations",
            json={"category": "isolamento", "since": "hoje", "intensity": "leve"},
            headers=trusted_headers,
        ).status_code
        == 201
    )

    revoke = client.post(f"/api/v1/trusted-people/{relationship_id}/revoke", headers=owner_headers)
    assert revoke.status_code == 200
    assert revoke.json()["status"] == "revoked"

    blocked = client.post(
        f"/api/v1/trusted-people/{relationship_id}/observations",
        json={"category": "isolamento", "since": "hoje", "intensity": "leve"},
        headers=trusted_headers,
    )
    assert blocked.status_code == 403


def test_unrelated_user_gets_not_found_not_forbidden(client, db_session):
    """
    Item 45 (cenário obrigatório): Pessoa A não tem NENHUMA relação
    com B e tenta acessar/agir mesmo assim. Resposta é 404, não 403 —
    403 confirmaria que o relacionamento existe; 404 não revela nada
    sobre a conta de B para quem não tem nenhum vínculo com ela.
    """
    _owner_headers, _trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    stranger_headers = _register_and_login(client, STRANGER_EMAIL, STRANGER_PASSWORD)

    response = client.post(
        f"/api/v1/trusted-people/{relationship_id}/observations",
        json={"category": "isolamento", "since": "hoje", "intensity": "leve"},
        headers=stranger_headers,
    )
    assert response.status_code == 404


def test_only_owner_can_update_permissions_or_revoke(client, db_session):
    """A própria pessoa de confiança não pode conceder permissão a si mesma."""
    _owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)

    response = client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": "record_observation", "is_granted": True}]},
        headers=trusted_headers,
    )
    assert response.status_code == 404  # não é o dono deste relacionamento


def test_owner_sees_observations_recorded_about_them(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": "record_observation", "is_granted": True}]},
        headers=owner_headers,
    )
    client.post(
        f"/api/v1/trusted-people/{relationship_id}/observations",
        json={"category": "mudanca_sono", "since": "2_3_dias", "intensity": "relevante"},
        headers=trusted_headers,
    )

    response = client.get(f"/api/v1/trusted-people/{relationship_id}/observations", headers=owner_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["category"] == "mudanca_sono"


def test_trusted_person_sees_accepted_relationship_in_watching_list(client, db_session):
    """
    ETAPA 27 (6ª leva): ponto de entrada do painel operacional — sem
    onboarding feito pelo dono, cai de volta pro e-mail do convite em
    vez de quebrar por falta de `Profile`.
    """
    _owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)

    response = client.get("/api/v1/trusted-people/watching", headers=trusted_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == relationship_id
    assert body[0]["owner_display_name"] == OWNER_EMAIL


def test_watching_list_excludes_pending_invite_and_owner_view(client, db_session):
    """
    Convite ainda pendente não dá acesso nenhum, então não deveria
    aparecer como conta acompanhada; e a lista é sempre do ponto de
    vista de quem é a pessoa de confiança, nunca do dono (que usa
    `GET /trusted-people` pra ver quem ELE convidou).
    """
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/trusted-people/invite", json={"email": TRUSTED_EMAIL}, headers=owner_headers)

    owner_watching = client.get("/api/v1/trusted-people/watching", headers=owner_headers)
    assert owner_watching.status_code == 200
    assert owner_watching.json() == []

    trusted_headers = _register_and_login(client, TRUSTED_EMAIL, TRUSTED_PASSWORD)
    trusted_watching = client.get("/api/v1/trusted-people/watching", headers=trusted_headers)
    assert trusted_watching.status_code == 200
    assert trusted_watching.json() == []
