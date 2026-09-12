import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import InterventionStatus, InterventionType


class Intervention(IdMixin, TimestampMixin, Base):
    """Item 23/24 — microintervenção sugerida ou sessão de body doubling."""
    __tablename__ = "interventions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[InterventionType] = mapped_column(nullable=False)
    status: Mapped[InterventionStatus] = mapped_column(default=InterventionStatus.SUGGESTED, nullable=False)

    related_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    related_deviation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deviation_events.id", ondelete="SET NULL"), nullable=True
    )
    # Item 24 — a quem foi pedido apoio (body doubling). Indexado
    # (ETAPA 30-32): dashboard_service e intervention_service filtram
    # por esta coluna direto pra achar pedidos de apoio pendentes.
    support_relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trusted_person_relationships.id", ondelete="SET NULL"), nullable=True,
        index=True,
    )

    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)

    result: Mapped["InterventionResult"] = relationship(
        back_populates="intervention", uselist=False, cascade="all, delete-orphan"
    )


class InterventionResult(IdMixin, Base):
    """Item 24 — "registrar se ajudou", nunca tratado como causalidade definitiva (item 26)."""
    __tablename__ = "intervention_results"

    intervention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interventions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    helped: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    intervention: Mapped[Intervention] = relationship(back_populates="result")
