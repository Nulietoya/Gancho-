"""ETAPA 22 — formas públicas de notificação e preferências (item 37)."""
import uuid
from datetime import datetime, time

from pydantic import BaseModel

from app.models.enums import NotificationChannel, NotificationPriority, NotificationType


class NotificationPreferenceUpdate(BaseModel):
    """
    Todos os campos opcionais — PATCH parcial, mesmo padrão de
    `TaskUpdate`. `None` explícito desliga a regra (sem horário
    silencioso / sem teto diário), nunca "não mude o que já estava".
    """
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    max_notifications_per_day: int | None = None
    channel_by_type: dict[NotificationType, NotificationChannel] | None = None


class NotificationPreferencePublic(BaseModel):
    quiet_hours_start: time | None
    quiet_hours_end: time | None
    max_notifications_per_day: int | None
    channel_by_type: dict[str, str] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationPublic(BaseModel):
    id: uuid.UUID
    type: NotificationType
    channel: NotificationChannel
    priority: NotificationPriority
    payload: dict
    grouped_with: uuid.UUID | None
    scheduled_for: datetime | None
    sent_at: datetime | None
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
