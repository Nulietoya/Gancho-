"""
ETAPA 23/24 — formas públicas dos dashboards. Nenhum destes schemas
calcula nada novo: cada um só organiza o que os motores das etapas
anteriores (baseline, desvio, estado, medicação, intervenções,
notificações) já produziram — mesmo raciocínio já registrado em
`explainability_service` (ETAPA 20), agora numa visão do dia (ETAPA
23, `DailyDashboard`) e numa visão histórica (ETAPA 24,
`AnalyticsDashboard`).

`TrustedDashboard` é a exceção: não é "tudo que existe", é só o que a
permissão concedida autoriza mostrar — ver a docstring da classe.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AlertState, DeviationEngine, IndicatorKey, MedicationEventStatus
from app.schemas.checkin import CheckInPublic
from app.schemas.explainability import TrustedAlertExplanation
from app.schemas.intervention import InterventionPublic
from app.schemas.notification import NotificationPublic


class MedicationDoseToday(BaseModel):
    """Uma dose esperada hoje — `status` é `None` quando ainda não existe nenhum `MedicationEvent` pra ela."""
    medication_id: uuid.UUID
    medication_name: str
    schedule_id: uuid.UUID
    time_of_day: str  # "HH:MM" já formatado — dashboard nunca deveria reformatar hora sozinho
    status: MedicationEventStatus | None


class DailyDashboard(BaseModel):
    state: AlertState
    state_reason: str
    state_since: datetime | None

    checkin_submitted_today: bool
    checkin: CheckInPublic | None

    medications_today: list[MedicationDoseToday]
    active_interventions: list[InterventionPublic]

    unread_notifications_count: int
    recent_notifications: list[NotificationPublic]


class AlertTimelineEntry(BaseModel):
    id: uuid.UUID
    state: AlertState
    reason_summary: str
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class IndicatorTrend(BaseModel):
    indicator_key: IndicatorKey
    label: str
    baseline_mean: float | None
    recent_value: float | None
    trend_slope: float | None
    sample_size: int | None


class DeviationTimelineEntry(BaseModel):
    id: uuid.UUID
    engine: DeviationEngine
    engine_label: str
    detected_at: datetime
    magnitude: float
    duration_days: int


class MedicationAdherenceSummary(BaseModel):
    period_days: int
    scheduled_count: int
    taken_count: int
    adherence_rate: float | None  # None = nenhuma dose agendada no período, nunca "aderência zero"


class InterventionStatsSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    helped_count: int
    not_helped_count: int
    no_result_count: int


class AnalyticsDashboard(BaseModel):
    period_days: int
    alert_timeline: list[AlertTimelineEntry]
    indicators: list[IndicatorTrend]
    deviation_timeline: list[DeviationTimelineEntry]
    medication_adherence: MedicationAdherenceSummary
    intervention_stats: InterventionStatsSummary


class TrustedDashboard(BaseModel):
    """
    Visão da PESSOA DE CONFIANÇA sobre o dono do relacionamento — nunca
    a mesma coisa que `DailyDashboard`/`AnalyticsDashboard` do dono.
    Documento de referência é explícito: "não mostraria histórico
    completo de humor, localização exata, conversas ou dados clínicos
    simplesmente porque alguém é pessoa de confiança" — cada seção
    abaixo só é preenchida se a permissão correspondente estiver
    concedida NESTE relacionamento; sem a permissão, a seção inteira
    vem `None` (nunca uma lista vazia fingindo "sem dado", que
    confundiria com "sem permissão").

    - `state`/`state_reason`: `RECEIVE_ALERT_YELLOW`/`RECEIVE_ALERT_RED`
      — VERDE nunca é sensível e sempre aparece; AMARELO/VERMELHO só
      aparecem se a pessoa tiver a permissão específica pra aquele
      estado (mesmo par permissão/estado já usado em
      `notification_service.notify_alert_state_change`).
    - `alert_explanation`: MESMO gate de `state`/`state_reason` (nunca
      um permission key novo) — por quê o estado é esse, com respaldo
      científico de por que esse tipo de desvio costuma acontecer,
      mas sem nenhum número por indicador (ver docstring de
      `TrustedAlertExplanation`, que é uma forma deliberadamente mais
      pobre que a explicação que o dono vê de si mesmo).
    - `medication_adherence`: `VIEW_MEDICATION` — só a taxa agregada
      dos últimos 30 dias, nunca o registro dose a dose.
    - `indicators`: `VIEW_SPECIFIC_INDICATORS` — só os indicadores
      explicitamente liberados em `Permission.indicator_scope`.
    - `alert_timeline`/`deviation_timeline`: `VIEW_FULL_HISTORY`.
    - `pending_support_requests`: `HELP_WITH_TASK` — pedidos de body
      doubling endereçados especificamente a esta pessoa, ainda
      pendentes de aceite.
    """
    relationship_id: uuid.UUID
    state: AlertState | None
    state_reason: str | None
    alert_explanation: TrustedAlertExplanation | None
    medication_adherence: MedicationAdherenceSummary | None
    indicators: list[IndicatorTrend] | None
    alert_timeline: list[AlertTimelineEntry] | None
    deviation_timeline: list[DeviationTimelineEntry] | None
    pending_support_requests: list[InterventionPublic] | None
