import uuid
from datetime import datetime, time

from sqlalchemy import DateTime, ForeignKey, Integer, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import NotificationChannel, NotificationPriority, NotificationType


class NotificationPreference(IdMixin, TimestampMixin, Base):
    """
    Item 37 — "não bombardear o usuário": horário silencioso, limite
    diário e canal preferido por tipo de notificação. Entidade
    auxiliar não listada nominalmente no documento, mas explicitamente
    pedida em texto (item 32: "considere também entidades auxiliares
    necessárias").
    """
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    quiet_hours_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    quiet_hours_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    max_notifications_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channel_by_type: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class Notification(IdMixin, Base):
    """Item 37. `grouped_with` permite agrupar várias notificações relacionadas em uma só entrega."""
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(nullable=False, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(nullable=False)
    priority: Mapped[NotificationPriority] = mapped_column(default=NotificationPriority.MEDIUM, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    grouped_with: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True
    )

    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
