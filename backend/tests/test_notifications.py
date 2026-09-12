"""
ETAPA 22 — notificações (item 37). Cobre a engine de anti-spam
(horário silencioso atravessando meia-noite, teto diário, prioridade
HIGH nunca contida), entrega adiada, leitura/marcação via API, e as
duas integrações de domínio que passaram a produzir notificação de
verdade nesta etapa: mudança de estado (`Alert`) e pedido de body
doubling endereçado (`Intervention`).
"""
import datetime

from app.core import email as email_module
from app.models.deviation import DeviationEvent
from app.models.enums import DeviationEngine
from app.models.notification import Notification
from app.models.trust import TrustedPersonRelationship
from app.services import notification_service
from tests.conftest import register_and_login as _register_and_login
from tests.conftest import user_id as _user_id

OWNER_EMAIL = "notif-dono@example.com"
OWNER_PASSWORD = "senhaForte123"
TRUSTED_EMAIL = "notif-confianca@example.com"
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


def _grant(client, owner_headers, relationship_id, permission_key):
    response = client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [{"permission_key": permission_key, "is_granted": True}]},
        headers=owner_headers,
    )
    assert response.status_code == 200, response.text


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
        explanation="Sua rotina mudou: seu humor mudou por 3 dia(s) seguidos.",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


# --- engine de anti-spam (unidade, direto no service) -----------------------


def test_preferences_default_created_on_first_access(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.get("/api/v1/notifications/preferences", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["quiet_hours_start"] is None
    assert body["max_notifications_per_day"] is None


def test_update_preferences_is_a_partial_patch(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.put(
        "/api/v1/notifications/preferences",
        json={"quiet_hours_start": "22:00:00", "quiet_hours_end": "07:00:00"},
        headers=headers,
    )
    response = client.put(
        "/api/v1/notifications/preferences", json={"max_notifications_per_day": 3}, headers=headers
    )
    body = response.json()
    assert body["quiet_hours_start"] == "22:00:00"  # não foi apagado pelo segundo PATCH
    assert body["max_notifications_per_day"] == 3


def test_notification_sent_immediately_with_no_preferences_set(client, db_session):
    from app.models.enums import NotificationPriority, NotificationType

    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    notification = notification_service.create_notification(
        db_session, owner_id, NotificationType.REMINDER, NotificationPriority.MEDIUM, {"message": "oi"}
    )
    assert notification.sent_at is not None
    assert notification.scheduled_for is None


def test_notification_deferred_during_overnight_quiet_hours(client, db_session):
    from app.models.enums import NotificationPriority, NotificationType

    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    client.put(
        "/api/v1/notifications/preferences",
        json={"quiet_hours_start": "22:00:00", "quiet_hours_end": "07:00:00"},
        headers=headers,
    )

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=23, minute=30, second=0, microsecond=0)
    notification = notification_service.create_notification(
        db_session, owner_id, NotificationType.REMINDER, NotificationPriority.MEDIUM, {"message": "oi"}, when=when
    )
    assert notification.sent_at is None
    assert notification.scheduled_for == when.replace(hour=7, minute=0) + datetime.timedelta(days=1)


def test_high_priority_bypasses_quiet_hours(client, db_session):
    from app.models.enums import NotificationPriority, NotificationType

    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    client.put(
        "/api/v1/notifications/preferences",
        json={"quiet_hours_start": "22:00:00", "quiet_hours_end": "07:00:00"},
        headers=headers,
    )

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=23, minute=30, second=0, microsecond=0)
    notification = notification_service.create_notification(
        db_session, owner_id, NotificationType.ALERT, NotificationPriority.HIGH, {"message": "vermelho"}, when=when
    )
    assert notification.sent_at == when
    assert notification.scheduled_for is None


def test_daily_cap_defers_extra_notification_to_next_day(client, db_session):
    from app.models.enums import NotificationPriority, NotificationType

    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    client.put("/api/v1/notifications/preferences", json={"max_notifications_per_day": 2}, headers=headers)

    when = datetime.datetime.now(datetime.timezone.utc)
    first = notification_service.create_notification(
        db_session, owner_id, NotificationType.TASK, NotificationPriority.MEDIUM, {"n": 1}, when=when
    )
    second = notification_service.create_notification(
        db_session, owner_id, NotificationType.TASK, NotificationPriority.MEDIUM, {"n": 2}, when=when
    )
    third = notification_service.create_notification(
        db_session, owner_id, NotificationType.TASK, NotificationPriority.MEDIUM, {"n": 3}, when=when
    )
    assert first.sent_at is not None
    assert second.sent_at is not None
    assert third.sent_at is None
    assert third.scheduled_for == when + datetime.timedelta(days=1)


def test_high_priority_never_contained_by_daily_cap(client, db_session):
    from app.models.enums import NotificationPriority, NotificationType

    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    client.put("/api/v1/notifications/preferences", json={"max_notifications_per_day": 1}, headers=headers)

    when = datetime.datetime.now(datetime.timezone.utc)
    notification_service.create_notification(
        db_session, owner_id, NotificationType.TASK, NotificationPriority.MEDIUM, {}, when=when
    )
    urgent = notification_service.create_notification(
        db_session, owner_id, NotificationType.ALERT, NotificationPriority.HIGH, {}, when=when
    )
    assert urgent.sent_at == when


def test_deliver_due_notifications_marks_deferred_ones_as_sent(client, db_session):
    from app.models.enums import NotificationPriority, NotificationType

    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    client.put(
        "/api/v1/notifications/preferences",
        json={"quiet_hours_start": "22:00:00", "quiet_hours_end": "07:00:00"},
        headers=headers,
    )

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=23, minute=0, second=0, microsecond=0)
    deferred = notification_service.create_notification(
        db_session, owner_id, NotificationType.REMINDER, NotificationPriority.MEDIUM, {}, when=when
    )
    assert deferred.sent_at is None

    later = deferred.scheduled_for + datetime.timedelta(minutes=1)
    delivered_count = notification_service.deliver_due_notifications(db_session, when=later)
    assert delivered_count == 1
    db_session.refresh(deferred)
    assert deferred.sent_at == later


def test_email_channel_override_actually_sends(client, db_session, monkeypatch):
    from app.models.enums import NotificationChannel, NotificationPriority, NotificationType

    sent = []
    monkeypatch.setattr(email_module, "send_email", lambda to, subject, body: sent.append((to, subject, body)))

    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    client.put(
        "/api/v1/notifications/preferences",
        json={"channel_by_type": {"reminder": "email"}},
        headers=headers,
    )

    notification = notification_service.create_notification(
        db_session, owner_id, NotificationType.REMINDER, NotificationPriority.MEDIUM, {"message": "lembrete"}
    )
    assert notification.channel == NotificationChannel.EMAIL
    assert len(sent) == 1
    assert sent[0][0] == OWNER_EMAIL


# --- listagem / leitura via API ---------------------------------------------


def test_list_and_mark_read(client, db_session):
    from app.models.enums import NotificationPriority, NotificationType

    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    created = notification_service.create_notification(
        db_session, owner_id, NotificationType.REMINDER, NotificationPriority.LOW, {"message": "oi"}
    )

    listed = client.get("/api/v1/notifications", headers=headers).json()
    assert any(n["id"] == str(created.id) for n in listed)
    assert next(n for n in listed if n["id"] == str(created.id))["read_at"] is None

    unread = client.get("/api/v1/notifications", params={"unread_only": True}, headers=headers).json()
    assert any(n["id"] == str(created.id) for n in unread)

    first_read = client.post(f"/api/v1/notifications/{created.id}/read", headers=headers).json()
    assert first_read["read_at"] is not None
    second_read = client.post(f"/api/v1/notifications/{created.id}/read", headers=headers).json()
    assert second_read["read_at"] == first_read["read_at"]  # idempotente

    unread_after = client.get("/api/v1/notifications", params={"unread_only": True}, headers=headers).json()
    assert all(n["id"] != str(created.id) for n in unread_after)


def test_notifications_are_private_to_their_owner(client, db_session):
    from app.models.enums import NotificationPriority, NotificationType

    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    created = notification_service.create_notification(
        db_session, owner_id, NotificationType.REMINDER, NotificationPriority.LOW, {}
    )

    stranger_headers = _register_and_login(client, "notif-estranho@example.com", "maisUmaSenha123")
    assert client.get("/api/v1/notifications", headers=stranger_headers).json() == []
    assert (
        client.post(f"/api/v1/notifications/{created.id}/read", headers=stranger_headers).status_code == 404
    )


# --- integração: Alert -> Notification --------------------------------------


def test_yellow_alert_notifies_owner(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    now = datetime.datetime.now(datetime.timezone.utc)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.STABILITY, now)

    response = client.post("/api/v1/alerts/sync", headers=headers)
    assert response.json()["state"] == "yellow"

    notifications = client.get("/api/v1/notifications", headers=headers).json()
    alert_notifs = [n for n in notifications if n["type"] == "alert"]
    assert len(alert_notifs) == 1
    assert alert_notifs[0]["priority"] == "medium"


def test_red_alert_notifies_trusted_person_with_permission_only(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    _grant(client, owner_headers, relationship_id, "receive_alert_red")

    owner_id = _user_id(db_session, OWNER_EMAIL)
    now = datetime.datetime.now(datetime.timezone.utc)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.STABILITY, now, magnitude=1.8)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.EXECUTIVE, now, magnitude=2.5)

    response = client.post("/api/v1/alerts/sync", headers=owner_headers)
    assert response.json()["state"] == "red"

    trusted_notifs = client.get("/api/v1/notifications", headers=trusted_headers).json()
    alert_notifs = [n for n in trusted_notifs if n["type"] == "alert"]
    assert len(alert_notifs) == 1
    assert alert_notifs[0]["priority"] == "high"
    assert alert_notifs[0]["payload"]["relationship_id"] == relationship_id


def test_yellow_alert_does_not_notify_trusted_person_without_permission(client, db_session):
    owner_headers, trusted_headers, _relationship_id = _fully_connected_relationship(client, db_session)
    # nenhuma permissão concedida
    owner_id = _user_id(db_session, OWNER_EMAIL)
    now = datetime.datetime.now(datetime.timezone.utc)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.STABILITY, now)

    client.post("/api/v1/alerts/sync", headers=owner_headers)

    trusted_notifs = client.get("/api/v1/notifications", headers=trusted_headers).json()
    assert trusted_notifs == []


def test_red_permission_does_not_leak_into_yellow_notifications(client, db_session):
    """RECEIVE_ALERT_RED concedida não implica RECEIVE_ALERT_YELLOW (item 45/70: permissões não se confundem)."""
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    _grant(client, owner_headers, relationship_id, "receive_alert_red")

    owner_id = _user_id(db_session, OWNER_EMAIL)
    now = datetime.datetime.now(datetime.timezone.utc)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.STABILITY, now)  # só 1 motor -> amarelo

    client.post("/api/v1/alerts/sync", headers=owner_headers)

    trusted_notifs = client.get("/api/v1/notifications", headers=trusted_headers).json()
    assert trusted_notifs == []


def test_resyncing_without_a_state_change_does_not_duplicate_notifications(client, db_session):
    """Mesmo princípio de `sync_alert_state` (só grava `Alert` novo quando o estado muda) vale pra notificação."""
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    _grant(client, owner_headers, relationship_id, "receive_alert_yellow")

    owner_id = _user_id(db_session, OWNER_EMAIL)
    now = datetime.datetime.now(datetime.timezone.utc)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.STABILITY, now)
    client.post("/api/v1/alerts/sync", headers=owner_headers)  # amarelo, notifica os dois

    stale = now - datetime.timedelta(days=30)
    _insert_deviation_event(db_session, owner_id, DeviationEngine.AVOIDANCE, stale)  # fora da janela, não conta
    client.post("/api/v1/alerts/sync", headers=owner_headers)  # nada novo -> ainda amarelo, sem duplicar

    owner_notifs = [n for n in client.get("/api/v1/notifications", headers=owner_headers).json() if n["type"] == "alert"]
    trusted_notifs = [n for n in client.get("/api/v1/notifications", headers=trusted_headers).json() if n["type"] == "alert"]
    assert len(owner_notifs) == 1
    assert len(trusted_notifs) == 1


# --- integração: body doubling -> SUPPORT_REQUEST ---------------------------


def test_body_doubling_request_notifies_the_addressed_trusted_person(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    _grant(client, owner_headers, relationship_id, "help_with_task")

    suggestion = client.post(
        "/api/v1/interventions/suggest", json={"type": "body_doubling_session"}, headers=owner_headers
    ).json()
    client.post(
        f"/api/v1/interventions/{suggestion['id']}/request",
        json={"support_relationship_id": relationship_id},
        headers=owner_headers,
    )

    trusted_notifs = client.get("/api/v1/notifications", headers=trusted_headers).json()
    support_notifs = [n for n in trusted_notifs if n["type"] == "support_request"]
    assert len(support_notifs) == 1
    assert support_notifs[0]["payload"]["intervention_id"] == suggestion["id"]


def test_microintervention_request_notifies_nobody(client):
    """Sem `support_relationship_id`, não há ninguém pra notificar (nenhuma outra pessoa envolvida)."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    suggestion = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    client.post(f"/api/v1/interventions/{suggestion['id']}/request", json={}, headers=headers)

    notifs = client.get("/api/v1/notifications", headers=headers).json()
    assert all(n["type"] != "support_request" for n in notifs)


# --- integração: reset de senha envia e-mail de verdade ---------------------


def test_password_reset_request_sends_email(client, monkeypatch):
    from app.services import auth_service

    sent = []
    monkeypatch.setattr(
        auth_service.email, "send_email", lambda to, subject, body: sent.append((to, subject, body))
    )

    _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post("/api/v1/auth/password-reset/request", json={"email": OWNER_EMAIL})
    assert response.status_code == 202
    assert len(sent) == 1
    to, subject, body = sent[0]
    assert to == OWNER_EMAIL
    assert "reset-password?token=" in body


def test_password_reset_request_for_unknown_email_sends_nothing(client, monkeypatch):
    from app.services import auth_service

    sent = []
    monkeypatch.setattr(
        auth_service.email, "send_email", lambda to, subject, body: sent.append((to, subject, body))
    )

    response = client.post("/api/v1/auth/password-reset/request", json={"email": "ninguem-notif@example.com"})
    assert response.status_code == 202  # nunca revela se o e-mail existe (mesma resposta dos dois casos)
    assert sent == []
