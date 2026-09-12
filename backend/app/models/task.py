import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import TaskEventType, TaskFailureReasonType, TaskOrigin, TaskPriority, TaskStatus


class Task(IdMixin, TimestampMixin, Base):
    """
    Item 7. `status` reflete o estado atual, mas nunca é a única
    fonte de verdade sobre a história da tarefa — toda transição gera
    uma TaskEvent (item 33). `postponed_count`/`attempt_count` são
    contadores desnormalizados (lidos com muita frequência pelo motor
    de função executiva, item 9) mantidos em sincronia pelo service
    que grava os eventos.
    """
    __tablename__ = "tasks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(default=TaskPriority.MEDIUM, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.PENDING, nullable=False, index=True)

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    postponed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Item 25 — origem da tarefa e, se veio de fora, de qual relacionamento.
    origin: Mapped[TaskOrigin] = mapped_column(default=TaskOrigin.SELF, nullable=False)
    source_relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trusted_person_relationships.id", ondelete="SET NULL"), nullable=True
    )
    # Item 24 — pessoa de apoio opcional (body doubling), diferente de quem sugeriu a tarefa.
    support_relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trusted_person_relationships.id", ondelete="SET NULL"), nullable=True
    )

    events: Mapped[list["TaskEvent"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskEvent(IdMixin, Base):
    """Item 33 — cada transição de estado é um evento imutável."""
    __tablename__ = "task_events"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[TaskEventType] = mapped_column(nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    task: Mapped[Task] = relationship(back_populates="events")
    failure_reason: Mapped["TaskFailureReason"] = relationship(
        back_populates="event", uselist=False, cascade="all, delete-orphan"
    )


class TaskFailureReason(IdMixin, Base):
    """
    Item 8 — por que a tarefa não foi feita. Ligado ao evento
    específico (postponed/cancelled), não só à tarefa, porque uma
    tarefa pode ser adiada mais de uma vez com motivos diferentes.
    """
    __tablename__ = "task_failure_reasons"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_events.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    reason: Mapped[TaskFailureReasonType] = mapped_column(nullable=False)
    custom_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    event: Mapped[TaskEvent] = relationship(back_populates="failure_reason")
