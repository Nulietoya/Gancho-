"""
ETAPA 25 (item 53) — ciclo de vida de conta (LGPD): exportação de
dados e exclusão. Exclusão virou apagamento físico de verdade em
2026-09-22 (era soft delete só até então — decisão revertida, ver
docstring de `account_service.delete_account`). Cobre o "retrato"
exportado refletir dado real, a auditoria de cada ação
(`DATA_EXPORTED`, `ACCOUNT_DELETED`, sobrevivendo anonimizada — FK
`SET NULL` — mesmo depois da conta sumir), a reconfirmação de senha
antes de apagar, o cascade de verdade sobre dado próprio, o e-mail
ficando livre pra reuso, e o caso da conta que é PESSOA DE CONFIANÇA
(não dona) de outra: o relacionamento sobrevive revogado, não fica
"aceito" com uma pessoa fantasma.
"""
from app.models.audit import AuditLog
from app.models.checkin import DailyCheckIn
from app.models.enums import AuditAction, RelationshipStatus
from app.models.trust import TrustedPersonRelationship
from app.models.user import User
from tests.conftest import register_and_login as _register_and_login
from tests.conftest import user_id as _user_id

EMAIL = "conta-dono@example.com"
PASSWORD = "senhaForte123"


def test_export_returns_expected_shape_and_reflects_data(client):
    headers = _register_and_login(client, "conta-export@example.com", "senhaForte123")
    client.post("/api/v1/checkins", json={"mood": 3}, headers=headers)
    client.post(
        "/api/v1/personal-plan", json={"title": "Plano", "description": "desc"}, headers=headers
    )

    response = client.get("/api/v1/account/export", headers=headers)
    assert response.status_code == 200
    body = response.json()

    for key in (
        "account",
        "profile",
        "checkins",
        "routine_history",
        "life_events",
        "medications",
        "interventions",
        "personal_plan",
        "trusted_relationships",
        "notifications",
    ):
        assert key in body

    assert body["account"]["email"] == "conta-export@example.com"
    assert len(body["checkins"]) == 1
    assert body["checkins"][0]["mood"] == 3
    assert body["personal_plan"]["title"] == "Plano"
    assert body["trusted_relationships"] == []


def test_export_writes_audit_log(client, db_session):
    headers = _register_and_login(client, "conta-export-audit@example.com", "senhaForte123")
    client.get("/api/v1/account/export", headers=headers)

    uid = _user_id(db_session, "conta-export-audit@example.com")
    log = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=uid, action=AuditAction.DATA_EXPORTED)
        .one_or_none()
    )
    assert log is not None


def test_delete_requires_correct_password(client):
    headers = _register_and_login(client, "conta-senha-errada@example.com", "senhaForte123")
    response = client.post("/api/v1/account/delete", json={"password": "senhaErrada"}, headers=headers)
    assert response.status_code == 401


def test_delete_blocks_subsequent_requests_and_login(client):
    headers = _register_and_login(client, EMAIL, PASSWORD)
    delete = client.post("/api/v1/account/delete", json={"password": PASSWORD}, headers=headers)
    assert delete.status_code == 200
    assert delete.json()["deleted"] is True

    # o mesmo access token, usado de novo, já não funciona mais — a
    # conta nem existe mais no banco pra get_current_user validar.
    blocked = client.get("/api/v1/account/export", headers=headers)
    assert blocked.status_code == 401

    login_attempt = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert login_attempt.status_code in (401, 403)


def test_delete_frees_email_for_reuse(client):
    """
    Motivação real da mudança: soft delete deixava `users.email`
    (único) preso pra sempre — contas de teste iam se acumulando sem
    jeito de reusar o mesmo endereço. Apagamento físico de verdade
    resolve isso.
    """
    email = "conta-reuso@example.com"
    headers = _register_and_login(client, email, PASSWORD)
    client.post("/api/v1/account/delete", json={"password": PASSWORD}, headers=headers)

    second_register = client.post("/api/v1/auth/register", json={"email": email, "password": "outraSenha123"})
    assert second_register.status_code == 201


def test_delete_cascades_own_data(client, db_session):
    headers = _register_and_login(client, "conta-cascade@example.com", "senhaForte123")
    client.post("/api/v1/checkins", json={"mood": 3}, headers=headers)
    uid = _user_id(db_session, "conta-cascade@example.com")

    client.post("/api/v1/account/delete", json={"password": "senhaForte123"}, headers=headers)

    assert db_session.query(User).filter_by(id=uid).one_or_none() is None
    assert db_session.query(DailyCheckIn).filter_by(user_id=uid).count() == 0


def test_delete_writes_audit_log_that_survives_anonymized(client, db_session):
    headers = _register_and_login(client, "conta-delete-audit@example.com", "senhaForte123")
    uid = _user_id(db_session, "conta-delete-audit@example.com")
    client.post("/api/v1/account/delete", json={"password": "senhaForte123"}, headers=headers)

    # a conta já não existe mais — o log sobrevive com actor/target
    # nulos (ondelete=SET NULL), não apagado junto.
    log = db_session.query(AuditLog).filter_by(action=AuditAction.ACCOUNT_DELETED).one_or_none()
    assert log is not None
    assert log.actor_user_id is None
    assert log.target_user_id is None
    assert db_session.query(User).filter_by(id=uid).one_or_none() is None


def test_delete_revokes_relationship_when_trusted_person_deletes_account(client, db_session):
    """
    Item 14/45: a conta apagada aqui é a PESSOA DE CONFIANÇA, não a
    dona. Sem tratamento manual, `trusted_user_id` (ondelete=SET NULL)
    ficaria nulo mas `status` continuaria "accepted" — uma pessoa de
    confiança fantasma que o dono ainda veria como ativa.
    `delete_account` revoga o relacionamento antes de apagar a conta.
    """
    owner_headers = _register_and_login(client, "dono-rede@example.com", "senhaForte123")
    invite = client.post(
        "/api/v1/trusted-people/invite",
        json={"email": "amiga-que-sai@example.com", "relationship_label": "amiga"},
        headers=owner_headers,
    ).json()

    trusted_headers = _register_and_login(client, "amiga-que-sai@example.com", "senhaForte123")
    accept = client.post(
        "/api/v1/trusted-people/accept", json={"invite_token": invite["invite_token"]}, headers=trusted_headers
    )
    assert accept.status_code == 200
    relationship_id = accept.json()["id"]

    client.post("/api/v1/account/delete", json={"password": "senhaForte123"}, headers=trusted_headers)

    relationship = db_session.query(TrustedPersonRelationship).filter_by(id=relationship_id).one()
    assert relationship.status == RelationshipStatus.REVOKED
    assert relationship.revoked_at is not None
    assert relationship.trusted_user_id is None


def test_delete_cascades_relationship_when_owner_deletes_account(client, db_session):
    """Espelho do teste acima: a conta apagada aqui é a DONA — o
    relacionamento inteiro cai junto (ondelete=CASCADE em
    owner_user_id), nada fica órfão."""
    owner_headers = _register_and_login(client, "dono-que-sai@example.com", "senhaForte123")
    invite = client.post(
        "/api/v1/trusted-people/invite",
        json={"email": "amiga-fica@example.com", "relationship_label": "amiga"},
        headers=owner_headers,
    ).json()
    relationship_id = invite["id"]

    client.post("/api/v1/account/delete", json={"password": "senhaForte123"}, headers=owner_headers)

    assert db_session.query(TrustedPersonRelationship).filter_by(id=relationship_id).one_or_none() is None
