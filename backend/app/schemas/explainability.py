"""
ETAPA 20 — forma pública da explicação (item 15/22). Nunca traz um
número que não exista já em `DeviationEvent`/`Alert`; é só a mesma
informação organizada de um jeito navegável (por motor, por
indicador, "seu normal" vs. "seu agora").
"""
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AlertState, DeviationEngine, IndicatorKey
from app.services.labels import ENGINE_LABELS, INDICATOR_LABELS


def _direction_label(mean: float | None, recent_value: float | None) -> str | None:
    if mean is None or recent_value is None:
        return None
    if recent_value > mean:
        return "acima do seu padrão habitual"
    if recent_value < mean:
        return "abaixo do seu padrão habitual"
    return "igual ao seu padrão habitual"


class IndicatorExplanation(BaseModel):
    indicator_key: str
    label: str
    baseline_mean: float | None
    recent_value: float | None
    streak_days: int | None
    direction: str | None  # "acima do seu padrão habitual" / "abaixo..." / "igual..."

    @classmethod
    def from_snapshot(cls, indicator_key_str: str, snapshot: dict) -> "IndicatorExplanation":
        try:
            indicator_key = IndicatorKey(indicator_key_str)
            label = INDICATOR_LABELS.get(indicator_key, indicator_key_str)
        except ValueError:
            label = indicator_key_str  # indicador desconhecido (ex.: dado antigo) — mostra a chave crua

        mean = snapshot.get("mean")
        recent_value = snapshot.get("recent_value")
        return cls(
            indicator_key=indicator_key_str,
            label=label,
            baseline_mean=mean,
            recent_value=recent_value,
            streak_days=snapshot.get("streak_days"),
            direction=_direction_label(mean, recent_value),
        )


class EngineExplanation(BaseModel):
    engine: DeviationEngine
    engine_label: str
    detected_at: datetime
    duration_days: int
    convergence_score: float | None
    explanation: str
    indicators: list[IndicatorExplanation]

    @classmethod
    def from_deviation_event(cls, event) -> "EngineExplanation":
        indicators = [
            IndicatorExplanation.from_snapshot(key, snapshot)
            for key, snapshot in event.baseline_snapshot.items()
        ]
        return cls(
            engine=event.engine,
            engine_label=ENGINE_LABELS.get(event.engine, event.engine.value),
            detected_at=event.detected_at,
            duration_days=event.duration_days,
            convergence_score=event.convergence_score,
            explanation=event.explanation,
            indicators=indicators,
        )


class AlertExplanation(BaseModel):
    alert_id: uuid.UUID
    state: AlertState
    reason_summary: str
    engines_count: int
    total_engines: int
    breadth_score: float | None  # engines_count / total_engines — "quantas áreas ao mesmo tempo"
    engines: list[EngineExplanation]

    @classmethod
    def from_alert(cls, alert, active_events: list, total_engines: int) -> "AlertExplanation":
        engines = [EngineExplanation.from_deviation_event(e) for e in active_events]
        return cls(
            alert_id=alert.id,
            state=alert.state,
            reason_summary=alert.reason_summary,
            engines_count=len(engines),
            total_engines=total_engines,
            breadth_score=(len(engines) / total_engines) if total_engines else None,
            engines=engines,
        )
