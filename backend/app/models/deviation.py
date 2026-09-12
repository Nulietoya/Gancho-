import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import AlertState, DeviationEngine


class DeviationEvent(IdMixin, Base):
    """
    Item 21 — saída do motor de desvio, um por execução por motor
    (Executivo/Evitação/Ativação/Estabilidade, item 9-12) que
    encontrar alteração relevante. `explanation` é texto pronto pra
    UI: item 22 exige que nenhum alerta apareça sem explicação
    ("seu padrão mudou porque...").
    """
    __tablename__ = "deviation_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engine: Mapped[DeviationEngine] = mapped_column(nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    domains_count: Mapped[int] = mapped_column(Integer, nullable=False)
    convergence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    triggering_indicator_keys: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    baseline_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    alerts: Mapped[list["Alert"]] = relationship(back_populates="triggering_deviation")


class Alert(IdMixin, TimestampMixin, Base):
    """
    Item 20 — evento de mudança de estado, não uma célula mutável:
    guardamos cada transição pra reconstruir a linha do tempo (item
    27: "o usuário precisa conseguir reconstruir o que aconteceu
    antes dessa piora"). O estado "atual" é sempre o Alert mais
    recente do usuário.
    """
    __tablename__ = "alerts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[AlertState] = mapped_column(nullable=False, index=True)
    triggering_deviation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deviation_events.id", ondelete="SET NULL"), nullable=True
    )
    reason_summary: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    triggering_deviation: Mapped[DeviationEvent | None] = relationship(back_populates="alerts")
