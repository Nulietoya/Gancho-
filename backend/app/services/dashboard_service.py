"""
Dashboards (ETAPA 23/24, itens 15/20/27). Nenhuma lógica nova aqui:
todo número exibido já foi calculado por um motor de etapa anterior
(baseline, desvio, estado, medicação, intervenções, notificações) —
dashboard só organiza pra exibição, mesmo raciocínio já registrado em
`explainability_service`.

ETAPA 23 (`build_daily_dashboard`) é a visão "agora" que o dono abre
todo dia: estado atual, check-in de hoje, doses de hoje, intervenções
em andamento, notificações não lidas.

ETAPA 24 (`build_analytics_dashboard`) é a visão histórica: linha do
tempo de estado, tendência por indicador, histórico de desvio, adesão
a medicação e resultado de intervenções num período (default 30 dias)
— o material pra gráfico que o item 27 do documento pede ("o usuário
precisa conseguir reconstruir o que aconteceu").

`build_trusted_dashboard` é a visão da PESSOA DE CONFIANÇA — a única
das três que não mostra tudo: cada seção só é montada se a permissão
correspondente estiver concedida (ver docstring de `TrustedDashboard`
no schema), nunca "pessoa de confiança vê tudo porque está
autenticada" (item 45/70, a mesma base de toda a ETAPA 7).

**Decisão de escopo registrada sobre "hoje"**: o dashboard diário usa
"hoje" no fuso do `Profile` (mesmo critério de `checkin_service`,
repetido aqui em vez de importado — são só duas linhas, não vale
acoplar os dois módulos por isso). Já o preenchimento automático de
dose esquecida (`scheduler_service`) sempre trabalhou em dia UTC —
inconsistência pequena e já existente entre os dois módulos, mantida
aqui de propósito em vez de "corrigida" por conta própria: mudar o dia
de referência do scheduler é decisão de produto (afeta quando uma dose
vira `FORGOT_TO_CONFIRM`), fora do escopo de um dashboard que só lê.
"""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import CheckInNotFound
from app.core.time import utc_now as _now
from app.models.deviation import Alert, DeviationEvent
from app.models.enums import (
    AlertState,
    InterventionStatus,
    MedicationEventStatus,
    PermissionKey,
)
from app.models.intervention import Intervention
from app.models.medication import Medication, MedicationEvent, MedicationSchedule
from app.models.notification import Notification
from app.models.trust import TrustedPersonRelationship
from app.models.user import User
from app.schemas.checkin import CheckInPublic
from app.schemas.dashboard import (
    AlertTimelineEntry,
    AnalyticsDashboard,
    DailyDashboard,
    DeviationTimelineEntry,
    IndicatorTrend,
    InterventionStatsSummary,
    MedicationAdherenceSummary,
    MedicationDoseToday,
    TrustedDashboard,
)
from app.schemas.intervention import InterventionPublic
from app.schemas.notification import NotificationPublic
from app.services import (
    alert_service,
    baseline_service,
    checkin_service,
    explainability_service,
    intervention_service,
    notification_service,
)
from app.services.labels import ENGINE_LABELS, INDICATOR_LABELS

DEFAULT_ANALYTICS_DAYS = 30
RECENT_NOTIFICATIONS_LIMIT = 5

_ACTIVE_INTERVENTION_STATUSES = {
    InterventionStatus.SUGGESTED,
    InterventionStatus.REQUESTED,
    InterventionStatus.ACCEPTED,
    InterventionStatus.STARTED,
}


def _today_for_user(user: User) -> date:
    """Mesmo raciocínio de `checkin_service._today_for_user` (ver docstring do módulo)."""
    tz_name = user.profile.timezone if user.profile else "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        return datetime.now(timezone.utc).date()
    return datetime.now(tz).date()


def _medications_today(db: Session, user: User, today: date) -> list[MedicationDoseToday]:
    schedules = db.scalars(
        select(MedicationSchedule)
        .join(Medication, MedicationSchedule.medication_id == Medication.id)
        .where(Medication.user_id == user.id, Medication.discontinued_at.is_(None))
        .order_by(MedicationSchedule.time_of_day)
    )
    doses: list[MedicationDoseToday] = []
    for schedule in schedules:
        if schedule.weekdays is not None and today.weekday() not in schedule.weekdays:
            continue
        event = db.scalar(
            select(MedicationEvent)
            .where(MedicationEvent.schedule_id == schedule.id, func.date(MedicationEvent.scheduled_for) == today)
            .order_by(MedicationEvent.scheduled_for.desc())
        )
        doses.append(
            MedicationDoseToday(
                medication_id=schedule.medication_id,
                medication_name=schedule.medication.name,
                schedule_id=schedule.id,
                time_of_day=schedule.time_of_day.strftime("%H:%M"),
                status=event.status if event is not None else None,
            )
        )
    return doses


def build_daily_dashboard(db: Session, user: User) -> DailyDashboard:
    alert = alert_service.get_current_alert(db, user)
    if alert is not None:
        state, state_reason, state_since = alert.state, alert.reason_summary, alert.created_at
    else:
        state = AlertState.GREEN
        state_reason = "Ainda sem dado suficiente para avaliar seu padrão."
        state_since = None

    today = _today_for_user(user)
    try:
        checkin = checkin_service.get_checkin(db, user, today)
    except CheckInNotFound:
        checkin = None

    active_interventions = [
        i for i in intervention_service.list_interventions(db, user) if i.status in _ACTIVE_INTERVENTION_STATUSES
    ]

    unread_count = db.scalar(
        select(func.count(Notification.id)).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    ) or 0
    recent_notifications = notification_service.list_notifications(db, user, limit=RECENT_NOTIFICATIONS_LIMIT)

    return DailyDashboard(
        state=state,
        state_reason=state_reason,
        state_since=state_since,
        checkin_submitted_today=checkin is not None,
        checkin=CheckInPublic.model_validate(checkin) if checkin is not None else None,
        medications_today=_medications_today(db, user, today),
        active_interventions=[InterventionPublic.model_validate(i) for i in active_interventions],
        unread_notifications_count=unread_count,
        recent_notifications=[NotificationPublic.model_validate(n) for n in recent_notifications],
    )


def _indicator_trends(db: Session, user: User) -> list[IndicatorTrend]:
    trends: list[IndicatorTrend] = []
    for baseline in baseline_service.list_active_baselines(db, user):
        metric = max(baseline.metrics, key=lambda m: m.computed_at, default=None)
        if metric is None:
            continue
        trends.append(
            IndicatorTrend(
                indicator_key=baseline.indicator_key,
                label=INDICATOR_LABELS.get(baseline.indicator_key, baseline.indicator_key.value),
                baseline_mean=metric.mean,
                recent_value=metric.recent_value,
                trend_slope=metric.trend_slope,
                sample_size=metric.sample_size,
            )
        )
    return trends


def _alert_timeline(db: Session, user: User, since: datetime) -> list[AlertTimelineEntry]:
    rows = db.scalars(
        select(Alert).where(Alert.user_id == user.id, Alert.created_at >= since).order_by(Alert.created_at.asc())
    )
    return [AlertTimelineEntry.model_validate(a) for a in rows]


def _deviation_timeline(db: Session, user: User, since: datetime) -> list[DeviationTimelineEntry]:
    rows = db.scalars(
        select(DeviationEvent)
        .where(DeviationEvent.user_id == user.id, DeviationEvent.detected_at >= since)
        .order_by(DeviationEvent.detected_at.asc())
    )
    return [
        DeviationTimelineEntry(
            id=e.id,
            engine=e.engine,
            engine_label=ENGINE_LABELS.get(e.engine, e.engine.value),
            detected_at=e.detected_at,
            magnitude=e.magnitude,
            duration_days=e.duration_days,
        )
        for e in rows
    ]


def _medication_adherence_summary(
    db: Session, user: User, since: datetime, period_days: int
) -> MedicationAdherenceSummary:
    base_query = (
        select(func.count(MedicationEvent.id))
        .join(MedicationSchedule, MedicationEvent.schedule_id == MedicationSchedule.id)
        .join(Medication, MedicationSchedule.medication_id == Medication.id)
        .where(Medication.user_id == user.id, MedicationEvent.scheduled_for >= since)
    )
    scheduled_count = db.scalar(base_query) or 0
    if not scheduled_count:
        return MedicationAdherenceSummary(
            period_days=period_days, scheduled_count=0, taken_count=0, adherence_rate=None
        )
    taken_count = db.scalar(base_query.where(MedicationEvent.status == MedicationEventStatus.TAKEN)) or 0
    return MedicationAdherenceSummary(
        period_days=period_days,
        scheduled_count=scheduled_count,
        taken_count=taken_count,
        adherence_rate=taken_count / scheduled_count,
    )


def _intervention_stats(db: Session, user: User, since: datetime) -> InterventionStatsSummary:
    interventions = list(
        db.scalars(select(Intervention).where(Intervention.user_id == user.id, Intervention.created_at >= since))
    )
    by_status: dict[str, int] = {}
    helped = not_helped = no_result = 0
    for i in interventions:
        by_status[i.status.value] = by_status.get(i.status.value, 0) + 1
        if i.result is None or i.result.helped is None:
            no_result += 1
        elif i.result.helped:
            helped += 1
        else:
            not_helped += 1
    return InterventionStatsSummary(
        total=len(interventions),
        by_status=by_status,
        helped_count=helped,
        not_helped_count=not_helped,
        no_result_count=no_result,
    )


def build_analytics_dashboard(db: Session, user: User, days: int = DEFAULT_ANALYTICS_DAYS) -> AnalyticsDashboard:
    since = _now() - timedelta(days=days)
    return AnalyticsDashboard(
        period_days=days,
        alert_timeline=_alert_timeline(db, user, since),
        indicators=_indicator_trends(db, user),
        deviation_timeline=_deviation_timeline(db, user, since),
        medication_adherence=_medication_adherence_summary(db, user, since, days),
        intervention_stats=_intervention_stats(db, user, since),
    )


def build_trusted_dashboard(db: Session, relationship: TrustedPersonRelationship) -> TrustedDashboard:
    owner = db.get(User, relationship.owner_user_id)
    granted = {p.permission_key for p in relationship.permissions if p.is_granted}
    indicator_scope = next(
        (
            p.indicator_scope
            for p in relationship.permissions
            if p.permission_key == PermissionKey.VIEW_SPECIFIC_INDICATORS and p.is_granted
        ),
        None,
    )

    state = state_reason = alert_explanation = None
    if owner is not None:
        alert = alert_service.get_current_alert(db, owner)
        if alert is not None:
            reveals = (
                alert.state == AlertState.GREEN
                or (alert.state == AlertState.YELLOW and PermissionKey.RECEIVE_ALERT_YELLOW in granted)
                or (alert.state == AlertState.RED and PermissionKey.RECEIVE_ALERT_RED in granted)
            )
            if reveals:
                state, state_reason = alert.state, alert.reason_summary
                alert_explanation = explainability_service.explain_alert_for_trusted_person(db, owner, alert)

    since = _now() - timedelta(days=DEFAULT_ANALYTICS_DAYS)

    medication_adherence = None
    if owner is not None and PermissionKey.VIEW_MEDICATION in granted:
        medication_adherence = _medication_adherence_summary(db, owner, since, DEFAULT_ANALYTICS_DAYS)

    indicators = None
    if owner is not None and PermissionKey.VIEW_SPECIFIC_INDICATORS in granted:
        allowed = set(indicator_scope) if indicator_scope else set()
        indicators = [t for t in _indicator_trends(db, owner) if t.indicator_key.value in allowed]

    alert_timeline = deviation_timeline = None
    if owner is not None and PermissionKey.VIEW_FULL_HISTORY in granted:
        alert_timeline = _alert_timeline(db, owner, since)
        deviation_timeline = _deviation_timeline(db, owner, since)

    pending_support_requests = None
    if PermissionKey.HELP_WITH_TASK in granted:
        rows = db.scalars(
            select(Intervention).where(
                Intervention.support_relationship_id == relationship.id,
                Intervention.status == InterventionStatus.REQUESTED,
            )
        )
        pending_support_requests = [InterventionPublic.model_validate(i) for i in rows]

    return TrustedDashboard(
        relationship_id=relationship.id,
        state=state,
        state_reason=state_reason,
        alert_explanation=alert_explanation,
        medication_adherence=medication_adherence,
        indicators=indicators,
        alert_timeline=alert_timeline,
        deviation_timeline=deviation_timeline,
        pending_support_requests=pending_support_requests,
    )
