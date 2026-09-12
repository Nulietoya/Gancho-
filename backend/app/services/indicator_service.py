"""
Ingestão de `FunctionalIndicator` (ETAPA 17, item 38). Este módulo é
a única ponte entre os dados brutos (check-in, evento de tarefa,
adesão a medicação) e o fato normalizado que o motor de
baseline/desvio lê — nenhum outro serviço grava em
`FunctionalIndicator` diretamente. Trocar como um indicador é
calculado é mexer só aqui, nunca no motor de baseline em si.

Chamado de dentro da mesma transação de quem gerou o dado
(`checkin_service`, `task_service`, `medication_service`) — sem
commit próprio, é responsabilidade de quem chama.

**Decisão de escopo registrada**: nem todo campo coletado tem um
`IndicatorKey` correspondente ainda. De `DailyCheckIn`, só
`mood`/`energy`/`anxiety`/`ability_to_start_tasks` mapeiam direto;
`sleep_quality` (escala 1-5, não é a mesma coisa que `SLEEP_HOURS`),
`willingness_to_interact` e `sense_of_functioning` ficam de fora por
enquanto — forçar `willingness_to_interact` em `SOCIAL_CONTACT`, por
exemplo, misturaria "vontade de interagir" (subjetivo) com "contato
social" (comportamental/contável), o que o item 38 pede pra manter
separado. `SLEEP_HOURS`, `WAKE_TIME_MINUTES`, `SLEEP_TIME_MINUTES`,
`LEFT_HOME`, `SOCIAL_CONTACT`, `ACTIVITY_LEVEL` e `AVOIDANCE_LOAD`
também ficam sem fonte de dado real ainda (dependem de rotina diária
declarada dia a dia ou sensor passivo, nenhum dos dois existe no MVP)
— o `FunctionalIndicator` sendo um fato normalizado por
`(usuário, indicador, dia, fonte)` significa que adicionar a fonte
depois é só escrever um novo `sync_*`, nunca reescrever o motor.
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.baseline import FunctionalIndicator
from app.models.checkin import DailyCheckIn
from app.models.enums import IndicatorKey, IndicatorSource, MedicationEventStatus, TaskEventType
from app.models.medication import Medication, MedicationEvent, MedicationSchedule
from app.models.task import Task, TaskEvent

_CHECKIN_FIELD_TO_INDICATOR = {
    "mood": IndicatorKey.MOOD,
    "energy": IndicatorKey.ENERGY,
    "anxiety": IndicatorKey.ANXIETY,
    "ability_to_start_tasks": IndicatorKey.ABILITY_TO_START_TASKS,
}

_TASK_EVENT_TYPE_TO_INDICATOR = {
    TaskEventType.STARTED: IndicatorKey.TASKS_STARTED_COUNT,
    TaskEventType.POSTPONED: IndicatorKey.TASKS_POSTPONED_COUNT,
    TaskEventType.COMPLETED: IndicatorKey.TASKS_COMPLETED_COUNT,
}


def _upsert_indicator(
    db: Session,
    user_id,
    indicator_key: IndicatorKey,
    source: IndicatorSource,
    recorded_for_date: date,
    value: float,
    unit: str | None = None,
) -> FunctionalIndicator:
    existing = db.scalar(
        select(FunctionalIndicator).where(
            FunctionalIndicator.user_id == user_id,
            FunctionalIndicator.indicator_key == indicator_key,
            FunctionalIndicator.recorded_for_date == recorded_for_date,
            FunctionalIndicator.source == source,
        )
    )
    if existing is not None:
        existing.value = value
        existing.unit = unit
        db.flush()
        return existing

    row = FunctionalIndicator(
        user_id=user_id,
        indicator_key=indicator_key,
        source=source,
        value=value,
        unit=unit,
        recorded_for_date=recorded_for_date,
        created_at=utc_now(),
    )
    db.add(row)
    db.flush()
    return row


def _delete_indicator_if_exists(
    db: Session, user_id, indicator_key: IndicatorKey, source: IndicatorSource, recorded_for_date: date
) -> None:
    existing = db.scalar(
        select(FunctionalIndicator).where(
            FunctionalIndicator.user_id == user_id,
            FunctionalIndicator.indicator_key == indicator_key,
            FunctionalIndicator.recorded_for_date == recorded_for_date,
            FunctionalIndicator.source == source,
        )
    )
    if existing is not None:
        db.delete(existing)
        db.flush()


def sync_checkin_indicators(db: Session, checkin: DailyCheckIn) -> None:
    """
    Bug corrigido numa revisão geral (achado ao auditar o próprio
    código, não reportado por teste): um PATCH que limpa um campo do
    check-in (ex.: `{"mood": null}`, depois de já ter enviado
    `mood` antes) atualizava `DailyCheckIn.mood` pra `None`, mas o
    `FunctionalIndicator` de `mood` daquele dia ficava intacto com o
    valor antigo — "sem dado" virava, silenciosamente, "o último dado
    que existiu". Baseline/motor de desvio liam esse valor obsoleto
    como se ainda fosse verdadeiro. Agora, campo voltando a `None`
    apaga o indicador daquele dia/fonte em vez de deixá-lo parado.
    """
    for field, indicator_key in _CHECKIN_FIELD_TO_INDICATOR.items():
        value = getattr(checkin, field)
        if value is not None:
            _upsert_indicator(
                db, checkin.user_id, indicator_key, IndicatorSource.CHECKIN, checkin.checkin_date, float(value)
            )
        else:
            _delete_indicator_if_exists(
                db, checkin.user_id, indicator_key, IndicatorSource.CHECKIN, checkin.checkin_date
            )


def sync_task_event_indicators(db: Session, user_id, event_date: date) -> None:
    """
    Recalcula do zero (nunca incrementa) as três contagens diárias a
    partir do próprio `TaskEvent` — a fonte de verdade é sempre o
    evento, `FunctionalIndicator` é só a projeção normalizada dele.
    """
    for event_type, indicator_key in _TASK_EVENT_TYPE_TO_INDICATOR.items():
        count = db.scalar(
            select(func.count(TaskEvent.id))
            .join(Task, TaskEvent.task_id == Task.id)
            .where(
                Task.user_id == user_id,
                TaskEvent.event_type == event_type,
                func.date(TaskEvent.occurred_at) == event_date,
            )
        )
        _upsert_indicator(db, user_id, indicator_key, IndicatorSource.TASK_EVENT, event_date, float(count or 0))


def sync_medication_adherence_indicator(db: Session, user_id, event_date: date) -> None:
    """
    Fração tomada/agendada no dia, entre 0 e 1. Sem dose agendada
    naquele dia (`total == 0`), não escreve indicador nenhum — "sem
    dado" é diferente de "aderência zero".
    """
    base_query = (
        select(func.count(MedicationEvent.id))
        .join(MedicationSchedule, MedicationEvent.schedule_id == MedicationSchedule.id)
        .join(Medication, MedicationSchedule.medication_id == Medication.id)
        .where(Medication.user_id == user_id, func.date(MedicationEvent.scheduled_for) == event_date)
    )
    total = db.scalar(base_query)
    if not total:
        return

    taken = db.scalar(base_query.where(MedicationEvent.status == MedicationEventStatus.TAKEN))
    _upsert_indicator(
        db,
        user_id,
        IndicatorKey.MEDICATION_ADHERENCE,
        IndicatorSource.MEDICATION_EVENT,
        event_date,
        (taken or 0) / total,
        unit="fraction",
    )


def list_indicator_values(
    db: Session,
    user_id,
    indicator_key: IndicatorKey | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 90,
) -> list[FunctionalIndicator]:
    stmt = select(FunctionalIndicator).where(FunctionalIndicator.user_id == user_id)
    if indicator_key is not None:
        stmt = stmt.where(FunctionalIndicator.indicator_key == indicator_key)
    if date_from is not None:
        stmt = stmt.where(FunctionalIndicator.recorded_for_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(FunctionalIndicator.recorded_for_date <= date_to)
    stmt = stmt.order_by(FunctionalIndicator.recorded_for_date.desc()).limit(limit)
    return list(db.scalars(stmt))
