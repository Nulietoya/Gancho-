import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import BaselineSource, BaselineStatus, IndicatorKey, IndicatorSource


class FunctionalIndicator(IdMixin, Base):
    """
    Fato normalizado, um valor por (usuário, indicador, dia, fonte).
    É a única tabela que o motor de baseline/desvio lê — ele não sabe
    (nem precisa saber) se o valor veio de um check-in, de um evento
    de tarefa ou de uma observação externa. Isso é o que permite
    trocar a lógica de cálculo sem tocar em nenhum outro módulo
    (item 38: "construa interfaces que permitam trocar o motor
    analítico sem reescrever o restante do produto").
    """
    __tablename__ = "functional_indicators"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "indicator_key", "recorded_for_date", "source",
            name="uq_indicator_user_key_date_source",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    indicator_key: Mapped[IndicatorKey] = mapped_column(nullable=False, index=True)
    source: Mapped[IndicatorSource] = mapped_column(nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    recorded_for_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Baseline(IdMixin, TimestampMixin, Base):
    """
    Item 5/32/56. Uma linha por (usuário, indicador, versão). Nunca é
    editada depois de calculada — uma recalibração cria uma nova
    versão e fecha `period_end`/marca `status=SUPERSEDED` na anterior,
    preservando o motivo de cada mudança de baseline ao longo do
    tempo (auditável, item 56: "o baseline antigo não pode
    eternamente classificar a nova rotina como anormal").
    """
    __tablename__ = "baselines"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    indicator_key: Mapped[IndicatorKey] = mapped_column(nullable=False, index=True)
    source: Mapped[BaselineSource] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[BaselineStatus] = mapped_column(default=BaselineStatus.ACTIVE, nullable=False, index=True)

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    metrics: Mapped[list["BaselineMetric"]] = relationship(
        back_populates="baseline", cascade="all, delete-orphan"
    )


class BaselineMetric(IdMixin, Base):
    """
    Item 5 — os números do baseline em um instante de recálculo
    (média, mediana, variabilidade, frequência, tendência, valor
    recente, diferença pro baseline). Uma tabela separada de Baseline
    porque o baseline é recalculado periodicamente (job noturno) sem
    trocar de versão — só quando muda estruturalmente é que uma nova
    Baseline (versão) é criada.
    """
    __tablename__ = "baseline_metrics"

    baseline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("baselines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)

    mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    median: Mapped[float | None] = mapped_column(Float, nullable=True)
    stddev: Mapped[float | None] = mapped_column(Float, nullable=True)
    frequency: Mapped[float | None] = mapped_column(Float, nullable=True)
    trend_slope: Mapped[float | None] = mapped_column(Float, nullable=True)
    recent_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    diff_from_baseline: Mapped[float | None] = mapped_column(Float, nullable=True)

    baseline: Mapped[Baseline] = relationship(back_populates="metrics")
