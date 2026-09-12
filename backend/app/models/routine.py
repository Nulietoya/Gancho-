import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import LifeEventType


class Routine(IdMixin, TimestampMixin, Base):
    """
    Referência autodeclarada (Fase 1 da Trilha A / onboarding): "como
    é o seu dia quando você está bem". Versionada — `version` sobe e
    a linha antiga fecha `period_end` quando o usuário atualiza a
    rotina após um evento de vida (item 56/57), em vez de sobrescrever
    o valor antigo.
    """
    __tablename__ = "routines"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    typical_wake_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    typical_sleep_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    goes_out_on_weekdays: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    social_contact_days_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typical_tasks_postponed_on_good_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Item 11 — o usuário escolhe quais domínios de ativação fazem
    # sentido pra ele; os demais nunca viram cobrança.
    selected_activation_domains: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class RoutineEvent(IdMixin, Base):
    """
    Log append-only de mudanças na rotina declarada (item 33 —
    arquitetura de eventos: não sobrescrever informação comportamental
    importante). Permite reconstruir "o que o usuário disse ser normal
    em cada momento", não só o valor atual.
    """
    __tablename__ = "routine_events"

    routine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    changed_field: Mapped[str] = mapped_column(String(80), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LifeEvent(IdMixin, TimestampMixin, Base):
    """
    Item 57 — contexto para não confundir uma transição de vida com
    deterioração (mudança de emprego, viagem, doença...).
    """
    __tablename__ = "life_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[LifeEventType] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
