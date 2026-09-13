"""
ETAPA 22 — ciclo automático. Cobre o preenchimento de doses de
medicação esquecidas (grace period, não-duplicação, respeito a dias
da semana, e nunca inventar histórico de antes de o horário existir)
e o ciclo noturno de desvio/alerta rodando por trás de `run_nightly_cycle`
sem precisar dos endpoints manuais. Também cobre o lembrete de dose em
tempo real (`send_medication_reminders`), incluindo o modo repetido
pensado pra dificuldade de perceber o tempo passar.
"""
import datetime

from app.models.baseline import FunctionalIndicator
from app.models.enums import IndicatorKey, MedicationEventStatus, NotificationPriority, NotificationType
from app.models.medication import MedicationEvent
from app.models.user import User
from app.services import notification_service, scheduler_service
from tests.conftest import post_checkin, register_and_login as _register_and_login, user_id as _user_id

OWNER_EMAIL = "sched-dono@example.com"
OWNER_PASSWORD = "senhaForte123"


def _create_medication_and_schedule(
    client, headers, time_of_day="08:00:00", weekdays=None, reminder_enabled=True, reminder_repeat_enabled=False
):
    med = client.post(
        "/api/v1/medications",
        json={
            "name": "sertralina",
            "reminder_enabled": reminder_enabled,
            "reminder_repeat_enabled": reminder_repeat_enabled,
        },
        headers=headers,
    ).json()
    payload = {"time_of_day": time_of_day}
    if weekdays is not None:
        payload["weekdays"] = weekdays
    schedule = client.post(f"/api/v1/medications/{med['id']}/schedules", json=payload, headers=headers).json()
    return med, schedule


def _owner(db_session, email=OWNER_EMAIL) -> User:
    return db_session.get(User, _user_id(db_session, email))


def test_creates_forgot_to_confirm_after_grace_period(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _med, schedule = _create_medication_and_schedule(client, headers, time_of_day="06:00:00")

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    created = scheduler_service.fill_forgotten_medication_events(db_session, _owner(db_session), when)
    assert created == 1

    event = db_session.query(MedicationEvent).filter_by(schedule_id=schedule["id"]).one()
    assert event.status == MedicationEventStatus.FORGOT_TO_CONFIRM
    assert event.confirmed_at is None


def test_within_grace_period_creates_nothing_yet(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _create_medication_and_schedule(client, headers, time_of_day="06:00:00")

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=7, minute=0, second=0, microsecond=0)
    created = scheduler_service.fill_forgotten_medication_events(db_session, _owner(db_session), when)
    assert created == 0


def test_does_not_duplicate_an_existing_event(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med, schedule = _create_medication_and_schedule(client, headers, time_of_day="06:00:00")

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    today_slot = when.replace(hour=6, minute=0, second=0, microsecond=0)

    client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": today_slot.isoformat(), "status": "taken"},
        headers=headers,
    )

    created = scheduler_service.fill_forgotten_medication_events(db_session, _owner(db_session), when)
    assert created == 0

    events = db_session.query(MedicationEvent).filter_by(schedule_id=schedule["id"]).all()
    assert len(events) == 1
    assert events[0].status == MedicationEventStatus.TAKEN


def test_respects_weekdays(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    other_weekday = (when.weekday() + 3) % 7  # nunca o dia de hoje
    _create_medication_and_schedule(client, headers, time_of_day="06:00:00", weekdays=[other_weekday])

    created = scheduler_service.fill_forgotten_medication_events(db_session, _owner(db_session), when)
    assert created == 0


def test_never_backfills_before_the_schedule_existed(client, db_session):
    """Um horário criado hoje não pode gerar dose 'esquecida' de dias em que ele nem existia."""
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _med, schedule = _create_medication_and_schedule(client, headers, time_of_day="06:00:00")

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    created = scheduler_service.fill_forgotten_medication_events(db_session, _owner(db_session), when)
    assert created == 1  # só o slot de hoje, nunca os dias anteriores ao horário existir

    events = db_session.query(MedicationEvent).filter_by(schedule_id=schedule["id"]).all()
    assert len(events) == 1
    assert events[0].scheduled_for.date() == when.date()


def test_forgotten_event_feeds_the_adherence_indicator(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    _create_medication_and_schedule(client, headers, time_of_day="06:00:00")

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    scheduler_service.fill_forgotten_medication_events(db_session, _owner(db_session), when)

    indicator = (
        db_session.query(FunctionalIndicator)
        .filter_by(user_id=owner_id, indicator_key=IndicatorKey.MEDICATION_ADHERENCE, recorded_for_date=when.date())
        .one()
    )
    assert indicator.value == 0.0  # 0 tomadas / 1 agendada


def test_run_nightly_cycle_syncs_alert_state_without_manual_endpoints(client, db_session, monkeypatch):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    for days_ago in range(12, 2, -1):
        post_checkin(client, headers, days_ago, mood=4)
    for days_ago in (2, 1, 0):
        post_checkin(client, headers, days_ago, mood=1)

    # restringe aos usuários deste teste — o Postgres de desenvolvimento
    # já tem contas reais de smoke tests manuais de etapas anteriores, e
    # processá-las de verdade aqui só deixaria o teste lento sem testar
    # nada a mais (mesmo cuidado já registrado em test_trusted_people.py
    # ao filtrar AuditLog por este teste específico).
    monkeypatch.setattr(scheduler_service, "_active_users", lambda db: [_owner(db_session)])

    # nada disparado manualmente: nem /deviation/run, nem /alerts/sync
    summary = scheduler_service.run_nightly_cycle(db_session)
    assert summary["users_processed"] == 1
    assert summary["failures"] == 0

    current_alert = client.get("/api/v1/alerts/current", headers=headers)
    assert current_alert.status_code == 200
    assert current_alert.json()["state"] == "yellow"


def test_run_nightly_cycle_isolates_failures_between_users(client, db_session, monkeypatch):
    _register_and_login(client, "sched-a@example.com", OWNER_PASSWORD)
    _register_and_login(client, "sched-b@example.com", OWNER_PASSWORD)
    user_a = _owner(db_session, "sched-a@example.com")
    user_b = _owner(db_session, "sched-b@example.com")
    monkeypatch.setattr(scheduler_service, "_active_users", lambda db: [user_a, user_b])

    original = scheduler_service.run_deviation_and_alert_cycle

    def _boom_for_a(db, user):
        if user.id == user_a.id:
            raise RuntimeError("falha simulada")
        return original(db, user)

    monkeypatch.setattr(scheduler_service, "run_deviation_and_alert_cycle", _boom_for_a)

    summary = scheduler_service.run_nightly_cycle(db_session)
    assert summary["failures"] == 1
    assert summary["users_processed"] == 1  # só o usuário B


def test_deliver_due_notifications_wrapper_delegates(client, db_session):
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
    later = deferred.scheduled_for + datetime.timedelta(minutes=1)
    count = scheduler_service.deliver_due_notifications(db_session, when=later)
    assert count == 1


def test_medication_reminder_not_sent_before_scheduled_time(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _create_medication_and_schedule(client, headers, time_of_day="08:00:00")

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=7, minute=59, second=0, microsecond=0)
    sent = scheduler_service.send_medication_reminders(db_session, _owner(db_session), when)
    assert sent == 0


def test_medication_reminder_sent_when_time_arrives(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med, schedule = _create_medication_and_schedule(client, headers, time_of_day="08:00:00")

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
    sent = scheduler_service.send_medication_reminders(db_session, _owner(db_session), when)
    assert sent == 1

    notifications = notification_service.list_notifications(db_session, _owner(db_session))
    assert len(notifications) == 1
    assert notifications[0].type == NotificationType.REMINDER
    assert notifications[0].priority == NotificationPriority.MEDIUM
    assert notifications[0].payload["medication_schedule_id"] == schedule["id"]
    assert notifications[0].payload["reminder_number"] == 1


def test_medication_reminder_never_sent_when_disabled_on_medication(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _create_medication_and_schedule(client, headers, time_of_day="08:00:00", reminder_enabled=False)

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    sent = scheduler_service.send_medication_reminders(db_session, _owner(db_session), when)
    assert sent == 0


def test_medication_reminder_without_repeat_mode_sends_only_once(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _create_medication_and_schedule(client, headers, time_of_day="08:00:00", reminder_repeat_enabled=False)
    owner = _owner(db_session)

    first = datetime.datetime.now(datetime.timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
    assert scheduler_service.send_medication_reminders(db_session, owner, first) == 1

    later = first + datetime.timedelta(minutes=30)
    assert scheduler_service.send_medication_reminders(db_session, owner, later) == 0

    notifications = notification_service.list_notifications(db_session, owner)
    assert len(notifications) == 1


def test_medication_reminder_repeat_mode_escalates_until_max(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _create_medication_and_schedule(client, headers, time_of_day="08:00:00", reminder_repeat_enabled=True)
    owner = _owner(db_session)
    scheduled = datetime.datetime.now(datetime.timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)

    assert scheduler_service.send_medication_reminders(db_session, owner, scheduled) == 1  # 1º lembrete

    just_after = scheduled + datetime.timedelta(minutes=1)
    assert scheduler_service.send_medication_reminders(db_session, owner, just_after) == 0  # ainda dentro do intervalo

    second_due = scheduled + datetime.timedelta(
        minutes=scheduler_service.MEDICATION_REMINDER_REPEAT_INTERVAL_MINUTES
    )
    assert scheduler_service.send_medication_reminders(db_session, owner, second_due) == 1  # 2º lembrete

    third_due = scheduled + datetime.timedelta(
        minutes=2 * scheduler_service.MEDICATION_REMINDER_REPEAT_INTERVAL_MINUTES
    )
    assert scheduler_service.send_medication_reminders(db_session, owner, third_due) == 1  # 3º lembrete (o máximo)

    fourth_due = scheduled + datetime.timedelta(
        minutes=3 * scheduler_service.MEDICATION_REMINDER_REPEAT_INTERVAL_MINUTES
    )
    assert scheduler_service.send_medication_reminders(db_session, owner, fourth_due) == 0  # já bateu o teto

    notifications = notification_service.list_notifications(db_session, owner)
    assert len(notifications) == scheduler_service.MEDICATION_REMINDER_MAX_REPEATS
    assert [n.payload["reminder_number"] for n in notifications] == [3, 2, 1]  # mais recente primeiro


def test_medication_reminder_stops_once_a_dose_event_exists(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    med, schedule = _create_medication_and_schedule(
        client, headers, time_of_day="08:00:00", reminder_repeat_enabled=True
    )
    owner = _owner(db_session)
    scheduled = datetime.datetime.now(datetime.timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)

    assert scheduler_service.send_medication_reminders(db_session, owner, scheduled) == 1

    client.post(
        f"/api/v1/medications/{med['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": scheduled.isoformat(), "status": "taken"},
        headers=headers,
    )

    later = scheduled + datetime.timedelta(minutes=scheduler_service.MEDICATION_REMINDER_REPEAT_INTERVAL_MINUTES)
    assert scheduler_service.send_medication_reminders(db_session, owner, later) == 0

    notifications = notification_service.list_notifications(db_session, owner)
    assert len(notifications) == 1  # só o lembrete de antes de confirmar, nada depois


def test_medication_reminder_never_sent_past_the_forgotten_dose_grace_window(client, db_session):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    _create_medication_and_schedule(client, headers, time_of_day="08:00:00", reminder_repeat_enabled=True)
    owner = _owner(db_session)

    past_grace = datetime.datetime.now(datetime.timezone.utc).replace(
        hour=8, minute=0, second=0, microsecond=0
    ) + datetime.timedelta(hours=scheduler_service.FORGOTTEN_DOSE_GRACE_HOURS)
    sent = scheduler_service.send_medication_reminders(db_session, owner, past_grace)
    assert sent == 0  # daqui pra frente é trabalho do backfill noturno (FORGOT_TO_CONFIRM), não de lembrete


def test_send_due_medication_reminders_processes_all_active_users(client, db_session, monkeypatch):
    headers_a = _register_and_login(client, "sched-med-a@example.com", OWNER_PASSWORD)
    headers_b = _register_and_login(client, "sched-med-b@example.com", OWNER_PASSWORD)
    _create_medication_and_schedule(client, headers_a, time_of_day="08:00:00")
    _create_medication_and_schedule(client, headers_b, time_of_day="08:00:00")

    user_a = _owner(db_session, "sched-med-a@example.com")
    user_b = _owner(db_session, "sched-med-b@example.com")
    monkeypatch.setattr(scheduler_service, "_active_users", lambda db: [user_a, user_b])

    when = datetime.datetime.now(datetime.timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
    summary = scheduler_service.send_due_medication_reminders(db_session, when)
    assert summary == {"users_processed": 2, "reminders_sent": 2, "failures": 0}
