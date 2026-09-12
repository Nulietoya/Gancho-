"""
Notificações (ETAPA 22, item 37 — "não bombardear o usuário"). Os
models (`Notification`, `NotificationPreference`) já existiam desde a
ETAPA 4; este módulo é a primeira coisa que efetivamente escreve
neles.

**O que "canal" significa aqui, honestamente**: não existe provedor de
push conectado neste MVP (exigiria token de dispositivo, que não é
modelado ainda) — `NotificationChannel.PUSH`/`IN_APP` só vivem como
linha no banco, lidas pelo cliente via `GET /notifications`.
`EMAIL` é o único canal com entrega de verdade, através de
`app/core/email.py`. Trocar isso por um provedor de push de verdade
no futuro é só trocar `_deliver` aqui, nunca o resto do sistema — o
mesmo raciocínio de "motor trocável sem reescrever o resto" já usado
em baseline/desvio.

**Anti-spam (item 37)**: toda notificação de prioridade
LOW/MEDIUM respeita horário silencioso (`quiet_hours_start/end`, que
pode virar a meia-noite) e teto diário (`max_notifications_per_day`)
— quando bloqueada por um dos dois, a notificação não é descartada,
é adiada (`scheduled_for`) e entregue depois por
`deliver_due_notifications` (chamada pelo job periódico). Prioridade
HIGH **nunca** é adiada nem contida pelo teto — é reservada pra
estado VERMELHO (protocolo de crise do item 20: "não pode ser
silenciado por configuração de conveniência").

**Simplificação deliberada**: uma notificação adiada por teto diário
vai pra "24h depois", sem checar de novo se aquele horário cai dentro
do horário silencioso do dia seguinte — evita uma cadeia de
recálculo sem fim para um caso de borda raro (registrado aqui, não
escondido).
"""
import uuid
from datetime import datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import email
from app.core.exceptions import NotificationNotFound
from app.core.time import utc_now as _now
from app.models.enums import (
    AlertState,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
    PermissionKey,
    RelationshipStatus,
)
from app.models.deviation import Alert
from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.services import trust_service

_DEFAULT_CHANNEL = NotificationChannel.PUSH


def get_or_create_preferences(db: Session, user_id: uuid.UUID) -> NotificationPreference:
    pref = db.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
    if pref is not None:
        return pref

    pref = NotificationPreference(user_id=user_id)
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref


def update_preferences(db: Session, user_id: uuid.UUID, changes: dict) -> NotificationPreference:
    pref = get_or_create_preferences(db, user_id)
    for field, value in changes.items():
        if field == "channel_by_type" and value is not None:
            value = {k.value: v.value for k, v in value.items()}
        setattr(pref, field, value)
    db.commit()
    db.refresh(pref)
    return pref


def _resolve_channel(pref: NotificationPreference, notif_type: NotificationType) -> NotificationChannel:
    if pref.channel_by_type:
        override = pref.channel_by_type.get(notif_type.value)
        if override is not None:
            return NotificationChannel(override)
    return _DEFAULT_CHANNEL


def _in_quiet_hours(pref: NotificationPreference, when: datetime) -> bool:
    if pref.quiet_hours_start is None or pref.quiet_hours_end is None:
        return False
    t = when.timetz().replace(tzinfo=None)
    start, end = pref.quiet_hours_start, pref.quiet_hours_end
    if start <= end:
        return start <= t < end
    return t >= start or t < end  # janela atravessa a meia-noite


def _quiet_hours_end_after(pref: NotificationPreference, when: datetime) -> datetime:
    end_time: time = pref.quiet_hours_end
    start_time: time = pref.quiet_hours_start
    if start_time <= end_time:
        target_date = when.date()
    else:
        target_date = when.date() if when.timetz().replace(tzinfo=None) < end_time else when.date() + timedelta(days=1)
    return datetime.combine(target_date, end_time, tzinfo=when.tzinfo)


def _count_sent_today(db: Session, user_id: uuid.UUID, when: datetime) -> int:
    return db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.sent_at.isnot(None),
            func.date(Notification.sent_at) == when.date(),
        )
    ) or 0


def _earliest_send_time(
    db: Session, pref: NotificationPreference, user_id: uuid.UUID, when: datetime, priority: NotificationPriority
) -> datetime | None:
    """None significa "pode mandar agora"; qualquer outro valor é pra quando adiar."""
    if priority == NotificationPriority.HIGH:
        return None
    if _in_quiet_hours(pref, when):
        return _quiet_hours_end_after(pref, when)
    if pref.max_notifications_per_day is not None and _count_sent_today(db, user_id, when) >= pref.max_notifications_per_day:
        return when + timedelta(days=1)
    return None


def _deliver_email(db: Session, user_id: uuid.UUID, notification: Notification) -> None:
    user = db.get(User, user_id)
    if user is None:
        return
    subject, body = _email_content(notification)
    email.send_email(user.email, subject, body)


def _email_content(notification: Notification) -> tuple[str, str]:
    text = notification.payload.get("reason_summary") or notification.payload.get("message") or ""
    return f"Gancho — {notification.type.value}", text


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    notif_type: NotificationType,
    priority: NotificationPriority,
    payload: dict,
    *,
    when: datetime | None = None,
) -> Notification:
    when = when or _now()
    pref = get_or_create_preferences(db, user_id)
    channel = _resolve_channel(pref, notif_type)
    defer_until = _earliest_send_time(db, pref, user_id, when, priority)

    notification = Notification(
        user_id=user_id,
        type=notif_type,
        channel=channel,
        priority=priority,
        payload=payload,
        scheduled_for=defer_until,
        sent_at=None if defer_until is not None else when,
        created_at=when,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    if notification.sent_at is not None and channel == NotificationChannel.EMAIL:
        _deliver_email(db, user_id, notification)
    return notification


def deliver_due_notifications(db: Session, when: datetime | None = None) -> int:
    """Chamada pelo job periódico (ETAPA 22) — entrega o que ficou represado por horário silencioso ou teto diário."""
    when = when or _now()
    due = db.scalars(
        select(Notification).where(
            Notification.sent_at.is_(None),
            Notification.scheduled_for.isnot(None),
            Notification.scheduled_for <= when,
        )
    )
    count = 0
    for notification in due:
        notification.sent_at = when
        if notification.channel == NotificationChannel.EMAIL:
            _deliver_email(db, notification.user_id, notification)
        count += 1
    if count:
        db.commit()
    return count


def list_notifications(db: Session, user: User, unread_only: bool = False, limit: int = 50) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def get_notification(db: Session, user: User, notification_id: uuid.UUID) -> Notification:
    notification = db.scalar(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
    )
    if notification is None:
        raise NotificationNotFound(str(notification_id))
    return notification


def mark_read(db: Session, user: User, notification_id: uuid.UUID) -> Notification:
    """Idempotente — mesmo padrão de `acknowledge_alert`."""
    notification = get_notification(db, user, notification_id)
    if notification.read_at is None:
        notification.read_at = _now()
        db.commit()
        db.refresh(notification)
    return notification


def notify_alert_state_change(db: Session, user: User, alert: Alert) -> None:
    """
    O "de propósito fora" registrado em `alert_service.sync_alert_state`
    (documentado ali desde a ETAPA 19): agora que existe canal de
    notificação de verdade, uma mudança de estado avisa o próprio dono
    sempre (inclusive alívio, voltar a VERDE) e a rede de confiança só
    em AMARELO/VERMELHO — e só quem tem `RECEIVE_ALERT_YELLOW`/
    `RECEIVE_ALERT_RED` concedida especificamente (item 45/70: nenhuma
    permissão nova, só as duas já modeladas desde a ETAPA 7 finalmente
    em uso).
    """
    owner_priority = {
        AlertState.GREEN: NotificationPriority.LOW,
        AlertState.YELLOW: NotificationPriority.MEDIUM,
        AlertState.RED: NotificationPriority.HIGH,
    }[alert.state]
    create_notification(
        db,
        user.id,
        NotificationType.ALERT,
        owner_priority,
        {"alert_id": str(alert.id), "state": alert.state.value, "reason_summary": alert.reason_summary},
    )

    if alert.state == AlertState.GREEN:
        return

    permission_key = (
        PermissionKey.RECEIVE_ALERT_RED if alert.state == AlertState.RED else PermissionKey.RECEIVE_ALERT_YELLOW
    )
    trusted_priority = NotificationPriority.HIGH if alert.state == AlertState.RED else NotificationPriority.MEDIUM

    for relationship in trust_service.list_relationships_for_owner(db, user):
        if relationship.status != RelationshipStatus.ACCEPTED or relationship.trusted_user_id is None:
            continue
        granted = any(p.permission_key == permission_key and p.is_granted for p in relationship.permissions)
        if not granted:
            continue
        create_notification(
            db,
            relationship.trusted_user_id,
            NotificationType.ALERT,
            trusted_priority,
            {
                "alert_id": str(alert.id),
                "state": alert.state.value,
                "relationship_id": str(relationship.id),
                "reason_summary": alert.reason_summary,
            },
        )
