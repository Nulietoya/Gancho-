"""
Regras de negócio de medicamentos e adesão (ETAPA 13, item 13 — o
mais sensível do produto até aqui: nada aqui gera recomendação de
dose, hora ou "tome agora". O sistema só registra o que a própria
pessoa informa sobre o próprio tratamento.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import MedicationNotFound, ScheduleNotFound
from app.core.time import utc_now as _now
from app.models.medication import Medication, MedicationEvent, MedicationSchedule
from app.models.user import User
from app.services import adherence_tips, indicator_service


def create_medication(db: Session, user: User, data: dict) -> Medication:
    medication = Medication(user_id=user.id, **data)
    db.add(medication)
    db.commit()
    db.refresh(medication)
    return medication


def list_medications(db: Session, user: User, include_discontinued: bool = False) -> list[Medication]:
    stmt = select(Medication).where(Medication.user_id == user.id)
    if not include_discontinued:
        stmt = stmt.where(Medication.discontinued_at.is_(None))
    stmt = stmt.order_by(Medication.created_at.desc())
    return list(db.scalars(stmt))


def get_medication(db: Session, user: User, medication_id: uuid.UUID) -> Medication:
    medication = db.scalar(
        select(Medication).where(Medication.id == medication_id, Medication.user_id == user.id)
    )
    if medication is None:
        raise MedicationNotFound(str(medication_id))
    return medication


def update_medication(db: Session, user: User, medication_id: uuid.UUID, changes: dict) -> Medication:
    medication = get_medication(db, user, medication_id)
    for field, value in changes.items():
        setattr(medication, field, value)
    db.commit()
    db.refresh(medication)
    return medication


def discontinue_medication(db: Session, user: User, medication_id: uuid.UUID) -> Medication:
    """Soft delete — idempotente; histórico de adesão continua valendo pro motor de estabilidade (item 12)."""
    medication = get_medication(db, user, medication_id)
    if medication.discontinued_at is None:
        medication.discontinued_at = _now()
        db.commit()
        db.refresh(medication)
    return medication


def create_schedule(db: Session, user: User, medication_id: uuid.UUID, data: dict) -> MedicationSchedule:
    medication = get_medication(db, user, medication_id)
    schedule = MedicationSchedule(medication_id=medication.id, **data)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def list_schedules(db: Session, user: User, medication_id: uuid.UUID) -> list[MedicationSchedule]:
    get_medication(db, user, medication_id)  # valida posse
    stmt = select(MedicationSchedule).where(MedicationSchedule.medication_id == medication_id)
    return list(db.scalars(stmt))


def get_schedule(db: Session, user: User, medication_id: uuid.UUID, schedule_id: uuid.UUID) -> MedicationSchedule:
    get_medication(db, user, medication_id)  # valida posse
    schedule = db.scalar(
        select(MedicationSchedule).where(
            MedicationSchedule.id == schedule_id, MedicationSchedule.medication_id == medication_id
        )
    )
    if schedule is None:
        raise ScheduleNotFound(str(schedule_id))
    return schedule


def update_schedule(
    db: Session, user: User, medication_id: uuid.UUID, schedule_id: uuid.UUID, changes: dict
) -> MedicationSchedule:
    schedule = get_schedule(db, user, medication_id, schedule_id)
    for field, value in changes.items():
        setattr(schedule, field, value)
    db.commit()
    db.refresh(schedule)
    return schedule


def create_event(
    db: Session, user: User, medication_id: uuid.UUID, schedule_id: uuid.UUID, data: dict
) -> MedicationEvent:
    schedule = get_schedule(db, user, medication_id, schedule_id)
    event = MedicationEvent(schedule_id=schedule.id, confirmed_at=_now(), **data)
    db.add(event)
    db.flush()
    indicator_service.sync_medication_adherence_indicator(db, user.id, event.scheduled_for.date())
    db.commit()
    db.refresh(event)
    return event


def adherence_tip_for_event(db: Session, event: MedicationEvent) -> str | None:
    """
    Pedido do usuário: quando o MESMO motivo de não-adesão se repete,
    sugerir uma estratégia concreta em vez de só registrar o motivo de
    novo. Nunca gravado em lugar nenhum — recomputado a cada evento a
    partir do histórico que já existe (mesmo raciocínio de
    `explainability_service`: nunca inventa dado novo). Olha pra TODOS
    os horários do mesmo medicamento (não só este `schedule_id`):
    esquecer a dose da manhã e a da noite pelo mesmo motivo é o mesmo
    padrão, não dois padrões diferentes.
    """
    if event.skip_reason is None:
        return None
    tip = adherence_tips.tip_for_reason(event.skip_reason)
    if tip is None:
        return None

    schedule = db.get(MedicationSchedule, event.schedule_id)
    if schedule is None:
        return None

    sibling_schedule_ids = select(MedicationSchedule.id).where(
        MedicationSchedule.medication_id == schedule.medication_id
    )
    recent_same_reason = db.scalars(
        select(MedicationEvent.id)
        .where(
            MedicationEvent.schedule_id.in_(sibling_schedule_ids),
            MedicationEvent.skip_reason == event.skip_reason,
        )
        .order_by(MedicationEvent.scheduled_for.desc())
        .limit(adherence_tips.REPEAT_THRESHOLD)
    ).all()

    if len(recent_same_reason) < adherence_tips.REPEAT_THRESHOLD:
        return None
    return tip


def list_events_for_medication(db: Session, user: User, medication_id: uuid.UUID) -> list[MedicationEvent]:
    get_medication(db, user, medication_id)  # valida posse
    stmt = (
        select(MedicationEvent)
        .join(MedicationSchedule, MedicationEvent.schedule_id == MedicationSchedule.id)
        .where(MedicationSchedule.medication_id == medication_id)
        .order_by(MedicationEvent.scheduled_for.desc())
    )
    return list(db.scalars(stmt))


def list_events_for_schedule(
    db: Session, user: User, medication_id: uuid.UUID, schedule_id: uuid.UUID
) -> list[MedicationEvent]:
    get_schedule(db, user, medication_id, schedule_id)  # valida posse
    stmt = (
        select(MedicationEvent)
        .where(MedicationEvent.schedule_id == schedule_id)
        .order_by(MedicationEvent.scheduled_for.desc())
    )
    return list(db.scalars(stmt))
