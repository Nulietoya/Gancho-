import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import BaselineSource, BaselineStatus, IndicatorKey, IndicatorSource


class RecomputeRequest(BaseModel):
    window_days: int = Field(default=30, ge=7, le=365)


class BaselineMetricPublic(BaseModel):
    id: uuid.UUID
    computed_at: datetime
    sample_size: int
    mean: float | None
    median: float | None
    stddev: float | None
    frequency: float | None
    trend_slope: float | None
    recent_value: float | None
    diff_from_baseline: float | None

    model_config = {"from_attributes": True}


class BaselinePublic(BaseModel):
    id: uuid.UUID
    indicator_key: IndicatorKey
    source: BaselineSource
    version: int
    window_days: int
    status: BaselineStatus
    period_start: date
    period_end: date | None
    latest_metric: BaselineMetricPublic | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_baseline(cls, baseline) -> "BaselinePublic":
        latest = max(baseline.metrics, key=lambda m: m.computed_at, default=None)
        return cls(
            id=baseline.id,
            indicator_key=baseline.indicator_key,
            source=baseline.source,
            version=baseline.version,
            window_days=baseline.window_days,
            status=baseline.status,
            period_start=baseline.period_start,
            period_end=baseline.period_end,
            latest_metric=BaselineMetricPublic.model_validate(latest) if latest else None,
        )


class BaselineVersionPublic(BaseModel):
    """Usado no histórico — traz TODAS as métricas já calculadas nessa versão, não só a última."""
    id: uuid.UUID
    version: int
    window_days: int
    status: BaselineStatus
    period_start: date
    period_end: date | None
    metrics: list[BaselineMetricPublic]

    model_config = {"from_attributes": True}


class FunctionalIndicatorPublic(BaseModel):
    id: uuid.UUID
    indicator_key: IndicatorKey
    source: IndicatorSource
    value: float
    unit: str | None
    recorded_for_date: date
    created_at: datetime

    model_config = {"from_attributes": True}
