"""
Lógica do ciclo automático (ETAPA 22) — o job noturno finalmente
resolvendo o que ficava manual desde a ETAPA 17/18/19/21: recalcular
baseline, rodar os 4 motores de desvio, sincronizar o estado
verde/amarelo/vermelho e preencher doses de medicação esquecidas,
pra todo usuário ativo, sem precisar que a própria pessoa lembre de
chamar os endpoints correspondentes.

Nenhuma função aqui sabe que existe um `BackgroundScheduler` por
trás — recebem uma `Session` já aberta, como qualquer outro service,
e por isso são testáveis com o mesmo `db_session` transacional do
resto da suíte. `app/core/scheduler.py` é a única peça que sabe de
APScheduler (fiação, não lógica) — mesma separação já usada entre
`app/api` e `app/services` no resto do projeto.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now as _now
from app.models.enums import MedicationEventStatus
from app.models.medication import Medication, MedicationEvent, MedicationSchedule
from app.models.user import User
from app.services import alert_service, deviation_service, indicator_service, notification_service

# Quantos dias pra trás o preenchimento de doses esquecidas olha —
# limita o "buraco" que uma agenda muito antiga sem uso geraria (item
# 65: não complicar sem necessidade, e nunca inventar histórico
# artificial demais pro passado).
FORGOTTEN_DOSE_LOOKBACK_DAYS = 3
# Quanto tempo depois do horário agendado uma dose sem nenhum
# registro vira FORGOT_TO_CONFIRM — nunca no mesmo instante, pra dar
# tempo real da pessoa confirmar antes.
FORGOTTEN_DOSE_GRACE_HOURS = 3


def _active_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.is_active.is_(True), User.deactivated_at.is_(None))))


def run_deviation_and_alert_cycle(db: Session, user: User) -> None:
    """O que já existia manualmente por trás de `POST /deviation/run*` + `POST /alerts/sync`, agora automático."""
    deviation_service.run_all_engines(db, user)
    alert_service.sync_alert_state(db, user)


def _weekday_matches(schedule: MedicationSchedule, day: date) -> bool:
    return schedule.weekdays is None or day.weekday() in schedule.weekdays


def fill_forgotten_medication_events(db: Session, user: User, when: datetime | None = None) -> int:
    """
    Item 13 — completa, nunca inventa: um horário agendado que passou
    há mais de `FORGOTTEN_DOSE_GRACE_HOURS` sem NENHUM registro (nem
    `taken`, nem `not_taken`, nem `skipped_deliberately`) vira
    `FORGOT_TO_CONFIRM` — ausência de confirmação é informação real
    (o motor de estabilidade não pode tratar "a pessoa nunca disse
    nada" como se fosse "tomou", que é o que aconteceria se o dia
    ficasse sem indicador nenhum), nunca é tratado como `not_taken`
    (essa é uma afirmação ativa da própria pessoa, item 13, nunca
    inferida pelo sistema).
    """
    when = when or _now()
    created = 0
    affected_dates: set[date] = set()

    schedules = db.scalars(
        select(MedicationSchedule)
        .join(Medication, MedicationSchedule.medication_id == Medication.id)
        .where(Medication.user_id == user.id, Medication.discontinued_at.is_(None))
    )
    for schedule in schedules:
        for days_ago in range(FORGOTTEN_DOSE_LOOKBACK_DAYS, -1, -1):
            day = (when - timedelta(days=days_ago)).date()
            if day < schedule.created_at.date():
                continue  # o horário nem existia nesse dia — nunca inventar histórico de antes de existir
            if not _weekday_matches(schedule, day):
                continue

            scheduled_for = datetime.combine(day, schedule.time_of_day, tzinfo=when.tzinfo)
            if scheduled_for > when - timedelta(hours=FORGOTTEN_DOSE_GRACE_HOURS):
                continue  # ainda dentro do prazo de graça, ou no futuro

            exists = db.scalar(
                select(MedicationEvent.id).where(
                    MedicationEvent.schedule_id == schedule.id,
                    MedicationEvent.scheduled_for == scheduled_for,
                )
            )
            if exists is not None:
                continue

            db.add(
                MedicationEvent(
                    schedule_id=schedule.id,
                    scheduled_for=scheduled_for,
                    status=MedicationEventStatus.FORGOT_TO_CONFIRM,
                )
            )
            created += 1
            affected_dates.add(day)

    if created:
        db.flush()
        for day in affected_dates:
            indicator_service.sync_medication_adherence_indicator(db, user.id, day)
        db.commit()
    return created


def run_nightly_cycle(db: Session, when: datetime | None = None) -> dict:
    """
    Um ciclo por usuário ativo, nunca uma query em lote misturando
    dados de várias pessoas — mesmo isolamento já seguido no resto do
    produto. Erro num usuário não derruba o ciclo dos outros: cada um
    roda no próprio try/except, com rollback isolado antes de seguir
    pro próximo.

    Os ids são coletados ANTES do loop, e cada usuário é recarregado
    (`db.get`) de novo a cada iteração — nunca reusa o objeto ORM
    obtido antes de um `rollback()` de uma iteração anterior. Depois
    de um rollback a sessão expira todos os objetos já carregados;
    continuar segurando a referência antiga levava a
    `ObjectDeletedError` num usuário seguinte perfeitamente saudável
    (achado escrevendo o teste de isolamento desta própria função).
    """
    when = when or _now()
    summary = {"users_processed": 0, "forgotten_events_created": 0, "failures": 0}
    user_ids = [user.id for user in _active_users(db)]

    for user_id in user_ids:
        try:
            user = db.get(User, user_id)
            if user is None:
                continue
            summary["forgotten_events_created"] += fill_forgotten_medication_events(db, user, when)
            run_deviation_and_alert_cycle(db, user)
            summary["users_processed"] += 1
        except Exception:
            db.rollback()
            summary["failures"] += 1
    return summary


def deliver_due_notifications(db: Session, when: datetime | None = None) -> int:
    return notification_service.deliver_due_notifications(db, when)
