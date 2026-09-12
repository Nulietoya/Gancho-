"""
Motor de baseline (ETAPA 17, itens 5/32/38/56). Lê exclusivamente de
`FunctionalIndicator` — nunca de check-in, tarefa ou medicação
diretamente, por isso pode ser trocado (outro método estatístico,
outra fonte) sem tocar em nenhum serviço de ingestão.

Duas operações bem diferentes, de propósito diferente (mesmo
raciocínio já usado em `routine_service`):
- `recompute_baseline`: recálculo periódico dos números dentro da
  MESMA versão — sobe um `BaselineMetric` novo, não mexe em
  `Baseline`. É o que rodaria num job noturno (ainda não existe
  scheduler — ETAPA 22).
- `recalibrate_baseline`: fecha a versão atual e abre outra do zero —
  reservado pra depois de uma virada de vida (item 56: "o baseline
  antigo não pode eternamente classificar a nova rotina como
  anormal"), o equivalente de `start_new_version` em rotinas.
"""
import statistics
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BaselineNotFound, NoIndicatorData
from app.core.time import utc_now as _now
from app.models.baseline import Baseline, BaselineMetric, FunctionalIndicator
from app.models.enums import BaselineSource, BaselineStatus, IndicatorKey
from app.models.user import User

DEFAULT_WINDOW_DAYS = 30


def _compute_metrics(values_by_date: dict[date, float]) -> dict:
    """
    Estatística deliberadamente simples (média, mediana, desvio
    padrão, frequência de registro, tendência linear, valor mais
    recente e o quanto ele se afasta da média) — item 65: não
    complicar sem necessidade. Um motor mais sofisticado (item 38)
    troca só esta função.
    """
    ordered_dates = sorted(values_by_date)
    values = [values_by_date[d] for d in ordered_dates]
    sample_size = len(values)

    mean = statistics.mean(values)
    median = statistics.median(values)
    stddev = statistics.stdev(values) if sample_size >= 2 else None

    # Tendência: regressão linear simples de valor por índice de dia
    # (não pelo índice na lista — dias sem registro contam como
    # "buraco" na tendência, não como posição consecutiva).
    trend_slope = None
    if sample_size >= 2:
        day_zero = ordered_dates[0]
        xs = [(d - day_zero).days for d in ordered_dates]
        x_mean = statistics.mean(xs)
        y_mean = mean
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
        denominator = sum((x - x_mean) ** 2 for x in xs)
        trend_slope = numerator / denominator if denominator else 0.0

    recent_value = values_by_date[ordered_dates[-1]]
    diff_from_baseline = recent_value - mean

    return {
        "sample_size": sample_size,
        "mean": mean,
        "median": median,
        "stddev": stddev,
        "frequency": None,  # preenchido pelo chamador, que sabe window_days
        "trend_slope": trend_slope,
        "recent_value": recent_value,
        "diff_from_baseline": diff_from_baseline,
    }


def _get_active_baseline(db: Session, user_id, indicator_key: IndicatorKey) -> Baseline | None:
    return db.scalar(
        select(Baseline).where(
            Baseline.user_id == user_id,
            Baseline.indicator_key == indicator_key,
            Baseline.status == BaselineStatus.ACTIVE,
        )
    )


def get_active_baseline(db: Session, user: User, indicator_key: IndicatorKey) -> Baseline:
    baseline = db.scalar(
        select(Baseline)
        .options(selectinload(Baseline.metrics))
        .where(
            Baseline.user_id == user.id,
            Baseline.indicator_key == indicator_key,
            Baseline.status == BaselineStatus.ACTIVE,
        )
    )
    if baseline is None:
        raise BaselineNotFound(indicator_key.value)
    return baseline


def list_active_baselines(db: Session, user: User) -> list[Baseline]:
    stmt = (
        select(Baseline)
        .options(selectinload(Baseline.metrics))
        .where(Baseline.user_id == user.id, Baseline.status == BaselineStatus.ACTIVE)
        .order_by(Baseline.indicator_key)
    )
    return list(db.scalars(stmt))


def get_baseline_history(db: Session, user: User, indicator_key: IndicatorKey) -> list[Baseline]:
    stmt = (
        select(Baseline)
        .options(selectinload(Baseline.metrics))
        .where(Baseline.user_id == user.id, Baseline.indicator_key == indicator_key)
        .order_by(Baseline.version.desc())
    )
    return list(db.scalars(stmt))


def recompute_baseline(
    db: Session,
    user: User,
    indicator_key: IndicatorKey,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> Baseline:
    baseline = _get_active_baseline(db, user.id, indicator_key)
    period_start = baseline.period_start if baseline is not None else date.today() - timedelta(days=window_days)
    window_start = date.today() - timedelta(days=window_days)

    rows = db.scalars(
        select(FunctionalIndicator).where(
            FunctionalIndicator.user_id == user.id,
            FunctionalIndicator.indicator_key == indicator_key,
            FunctionalIndicator.recorded_for_date >= window_start,
        )
    )
    values_by_date: dict[date, float] = {}
    for row in rows:
        values_by_date[row.recorded_for_date] = row.value  # mais de uma fonte no mesmo dia: última vence

    if not values_by_date:
        raise NoIndicatorData(indicator_key.value)

    metrics = _compute_metrics(values_by_date)
    metrics["frequency"] = metrics["sample_size"] / window_days

    if baseline is None:
        baseline = Baseline(
            user_id=user.id,
            indicator_key=indicator_key,
            source=BaselineSource.SELF_DECLARED,
            version=1,
            window_days=window_days,
            status=BaselineStatus.ACTIVE,
            period_start=period_start,
        )
        db.add(baseline)
        db.flush()

    db.add(
        BaselineMetric(
            baseline_id=baseline.id,
            computed_at=_now(),
            sample_size=metrics["sample_size"],
            mean=metrics["mean"],
            median=metrics["median"],
            stddev=metrics["stddev"],
            frequency=metrics["frequency"],
            trend_slope=metrics["trend_slope"],
            recent_value=metrics["recent_value"],
            diff_from_baseline=metrics["diff_from_baseline"],
        )
    )
    db.commit()
    db.refresh(baseline)
    return baseline


def recalibrate_baseline(db: Session, user: User, indicator_key: IndicatorKey) -> Baseline:
    """
    Item 56/57 — virada de vida: fecha a versão ativa (se existir) e
    abre outra do zero, sem métrica ainda (chamar `recompute_baseline`
    em seguida, quando já houver dado novo suficiente no período).
    """
    today = date.today()
    current = _get_active_baseline(db, user.id, indicator_key)
    next_version = 1
    window_days = DEFAULT_WINDOW_DAYS
    if current is not None:
        current.status = BaselineStatus.SUPERSEDED
        current.period_end = today
        next_version = current.version + 1
        window_days = current.window_days

    baseline = Baseline(
        user_id=user.id,
        indicator_key=indicator_key,
        source=BaselineSource.SELF_DECLARED,
        version=next_version,
        window_days=window_days,
        status=BaselineStatus.ACTIVE,
        period_start=today,
    )
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline
