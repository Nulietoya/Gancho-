"""
ETAPA 26 (item 31) — trilha de auditoria. Cobre as três lacunas
fechadas nesta etapa (LOGIN, PASSWORD_CHANGE, CRITICAL_ALERT — o enum
existia desde o início, mas nada gravava essas linhas até aqui) e a
consulta paginada, incluindo o caso em que uma pessoa de confiança é
quem gera a linha (`actor_is_self=False`) sem revelar qual delas.
"""
import datetime

from app.models.audit import AuditLog
from app.models.deviation import DeviationEvent
from app.models.enums import AuditAction, DeviationEngine
from app.models.trust import TrustedPersonRelationship
from tests.conftest import register_and_login as _register_and_login
from tests.conftest import user_id as _user_id


def _insert_deviation_event(db_session, owner_id, engine, detected_at, magnitude=2.0):
    event = DeviationEvent(
        user_id=owner_id,
        engine=engine,
        detected_at=detected_at,
        magnitude=magnitude,
        duration_days=3,
        domains_count=1,
        convergence_score=0.5,
        triggering_indicator_keys=["mood"],
        baseline_snapshot={"mood": {"mean": 3.0}},
        explanation="teste",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


# --- gravação -----------------------------------------------------------


def test_login_writes_audit_log(client, db_session):
    email, password = "audit-login@example.com", "senhaForte123"
    _register_and_login(client, email, password)

    uid = _user_id(db_session, email)
    # 2 linhas: uma do register+login embutido no helper, o helper só
    # loga uma vez de fato (register não audita) — confere que existe
    # pelo menos uma linha de LOGIN.
    logs = db_session.query(AuditLog).filter_by(target_user_id=uid, action=AuditAction.LOGIN).all()
    assert len(logs) >= 1
    assert logs[0].actor_user_id == uid


def test_change_password_writes_audit_log(client, db_session):
    email, password = "audit-troca-senha@example.com", "senhaForte123"
    headers = _register_and_login(client, email, password)
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": password, "new_password": "outraSenhaForte456"},
        headers=headers,
    )
    assert response.status_code == 204

    uid = _user_id(db_session, email)
    log = (
        db_session.query(AuditLog)
        .filter_by(target_user_id=uid, action=AuditAction.PASSWORD_CHANGE)
        .one_or_none()
    )
    assert log is not None
    assert log.log_metadata == {"via": "change_password"}


def test_critical_alert_writes_audit_log_only_on_red_transition(client, db_session):
    email, password = "audit-alerta@example.com", "senhaForte123"
    headers = _register_and_login(client, email, password)
    owner_id = _user_id(db_session, email)
    now = datetime.datetime.now(datetime.timezone.utc)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.STABILITY, now, magnitude=1.8)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.EXECUTIVE, now, magnitude=2.5)

    response = client.post("/api/v1/alerts/sync", headers=headers)
    assert response.json()["state"] == "red"

    logs = (
        db_session.query(AuditLog)
        .filter_by(target_user_id=owner_id, action=AuditAction.CRITICAL_ALERT)
        .all()
    )
    assert len(logs) == 1

    # reavaliar sem mudança de estado não duplica a auditoria
    client.post("/api/v1/alerts/sync", headers=headers)
    logs_again = (
        db_session.query(AuditLog)
        .filter_by(target_user_id=owner_id, action=AuditAction.CRITICAL_ALERT)
        .all()
    )
    assert len(logs_again) == 1


# --- consulta -------------------------------------------------------------


def test_list_audit_log_empty_by_default(client):
    headers = _register_and_login(client, "audit-vazio@example.com", "senhaForte123")
    response = client.get("/api/v1/audit-log", headers=headers)
    assert response.status_code == 200
    # o próprio login já gerou uma linha
    body = response.json()
    assert len(body) == 1
    assert body[0]["action"] == "login"
    assert body[0]["actor_is_self"] is True


def test_list_audit_log_reflects_own_actions_newest_first(client):
    email, password = "audit-cronologia@example.com", "senhaForte123"
    headers = _register_and_login(client, email, password)
    client.post(
        "/api/v1/auth/change-password",
        json={"current_password": password, "new_password": "outraSenha456"},
        headers=headers,
    )

    body = client.get("/api/v1/audit-log", headers=headers).json()
    actions = [entry["action"] for entry in body]
    assert actions[0] == "password_change"
    assert "login" in actions


def test_list_audit_log_respects_limit(client):
    email, password = "audit-limite@example.com", "senhaForte123"
    headers = _register_and_login(client, email, password)
    for i in range(3):
        client.post(
            "/api/v1/auth/change-password",
            json={"current_password": password if i == 0 else f"senha{i}Forte", "new_password": f"senha{i + 1}Forte"},
            headers=headers,
        )

    response = client.get("/api/v1/audit-log?limit=2", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_audit_log_only_shows_own_account_never_other_users(client):
    headers_a = _register_and_login(client, "audit-isolamento-a@example.com", "senhaForte123")
    _register_and_login(client, "audit-isolamento-b@example.com", "senhaForte123")

    body = client.get("/api/v1/audit-log", headers=headers_a).json()
    assert len(body) == 1  # só o próprio login, nunca o de outro usuário


def test_list_audit_log_shows_actor_is_self_false_for_trusted_person_actions(client, db_session):
    owner_email, owner_password = "audit-dono@example.com", "senhaForte123"
    trusted_email, trusted_password = "audit-confianca@example.com", "outraSenhaForte123"

    owner_headers = _register_and_login(client, owner_email, owner_password)
    client.post("/api/v1/trusted-people/invite", json={"email": trusted_email}, headers=owner_headers)
    raw_token = (
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=trusted_email).one().invite_token
    )
    trusted_headers = _register_and_login(client, trusted_email, trusted_password)
    client.post("/api/v1/trusted-people/accept", json={"invite_token": raw_token}, headers=trusted_headers)
    relationship_id = str(
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=trusted_email).one().id
    )

    client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": "record_observation", "is_granted": True}]},
        headers=owner_headers,
    )
    client.post(
        f"/api/v1/trusted-people/{relationship_id}/observations",
        json={"category": "isolamento", "since": "2_3_dias", "intensity": "leve"},
        headers=trusted_headers,
    )

    body = client.get("/api/v1/audit-log", headers=owner_headers).json()
    observation_entries = [e for e in body if e["action"] == "external_observation_recorded"]
    assert len(observation_entries) == 1
    assert observation_entries[0]["actor_is_self"] is False
