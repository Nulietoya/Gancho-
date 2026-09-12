"""
ETAPA 25 (item 53) — ciclo de vida de conta (LGPD): exportação de
dados e exclusão (soft delete). Cobre o "retrato" exportado refletir
dado real, a auditoria de cada ação (`DATA_EXPORTED`,
`ACCOUNT_DELETION_REQUESTED`), a reconfirmação de senha antes de
desativar, a idempotência da desativação e o efeito real (login e
`get_current_user` param de funcionar imediatamente — `get_current_user`
sempre confere `is_active`/`deactivated_at` contra o banco, nunca só o
claim do token).
"""
from app.models.audit import AuditLog
from app.models.enums import AuditAction
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


def test_deactivate_requires_correct_password(client):
    headers = _register_and_login(client, "conta-senha-errada@example.com", "senhaForte123")
    response = client.post(
        "/api/v1/account/deactivate", json={"password": "senhaErrada"}, headers=headers
    )
    assert response.status_code == 401


def test_deactivate_blocks_subsequent_requests_and_login(client):
    headers = _register_and_login(client, EMAIL, PASSWORD)
    deactivate = client.post("/api/v1/account/deactivate", json={"password": PASSWORD}, headers=headers)
    assert deactivate.status_code == 200
    assert deactivate.json()["deactivated"] is True

    # o mesmo access token, usado de novo, já não funciona mais —
    # get_current_user confere is_active/deactivated_at contra o banco
    # a cada chamada, nunca só o claim do token.
    blocked = client.get("/api/v1/account/export", headers=headers)
    assert blocked.status_code == 401

    login_attempt = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert login_attempt.status_code == 403


def test_deactivate_is_idempotent(client, db_session):
    headers = _register_and_login(client, "conta-idempotente@example.com", "senhaForte123")
    first = client.post("/api/v1/account/deactivate", json={"password": "senhaForte123"}, headers=headers)
    assert first.status_code == 200

    # segunda chamada via API com o mesmo token já bloqueado dá 401
    # (esperado — não há mais sessão válida pra repetir a ação via
    # HTTP); o que este teste verifica é que a camada de serviço em si
    # não quebra ao ser chamada de novo numa conta já desativada —
    # reusa a MESMA sessão transacional do teste (`db_session`, a
    # mesma que o `client` usa via override de `get_db`), nunca uma
    # sessão própria contra o Postgres real (ver docstring de
    # `db_session` em conftest.py sobre o padrão de SAVEPOINT).
    from app.models.user import User
    from app.services import account_service

    user = db_session.query(User).filter_by(email="conta-idempotente@example.com").one()
    result = account_service.deactivate_account(db_session, user, "senhaForte123")
    assert result.deactivated_at is not None


def test_deactivate_writes_audit_log(client, db_session):
    headers = _register_and_login(client, "conta-deactivate-audit@example.com", "senhaForte123")
    client.post("/api/v1/account/deactivate", json={"password": "senhaForte123"}, headers=headers)

    uid = _user_id(db_session, "conta-deactivate-audit@example.com")
    log = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=uid, action=AuditAction.ACCOUNT_DELETION_REQUESTED)
        .one_or_none()
    )
    assert log is not None
