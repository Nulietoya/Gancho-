import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import MedicationEventStatus, MedicationSkipReason


class Medication(IdMixin, TimestampMixin, Base):
    """
    Item 13. Guarda só o que o usuário informou sobre o próprio
    tratamento — nunca uma instrução de dose gerada pelo sistema.
    `discontinued_at` em vez de exclusão física: histórico de
    medicação é relevante pro motor de estabilidade (item 12) mesmo
    depois de suspensa.
    """
    __tablename__ = "medications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    dosage_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    discontinued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    schedules: Mapped[list["MedicationSchedule"]] = relationship(
        back_populates="medication", cascade="all, delete-orphan"
    )


class MedicationSchedule(IdMixin, TimestampMixin, Base):
    __tablename__ = "medication_schedules"

    medication_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    weekdays: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer), nullable=True
    )  # None = todos os dias; senão lista de 0(seg)-6(dom)

    medication: Mapped[Medication] = relationship(back_populates="schedules")
    events: Mapped[list["MedicationEvent"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class MedicationEvent(IdMixin, Base):
    """
    Item 13 — "registre apenas adesão conforme plano informado pelo
    usuário". Nunca uma linha aqui vira recomendação de tomar agora
    ou tomar dose dobrada (isso é regra de produto, reforçada em
    services/, não só documentação).
    """
    __tablename__ = "medication_events"

    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medication_schedules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[MedicationEventStatus] = mapped_column(nullable=False)
    skip_reason: Mapped[MedicationSkipReason | None] = mapped_column(nullable=True)
    custom_reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    schedule: Mapped[MedicationSchedule] = relationship(back_populates="events")
