"""
Regras de negócio de rotina de referência (ETAPA 12, itens 4/11/56/57).

Duas formas de mudar a rotina, de propósito diferente:
- `update_routine` (PATCH): edição corriqueira da versão atual — cada
  campo alterado vira um `RoutineEvent` (item 33: histórico
  reconstruível), mas a versão em si não muda.
- `start_new_version`: virada de vida (mudança de emprego, item
  56/57) — fecha a versão atual (`period_end`) e abre uma nova do
  zero, pra um desvio do baseline anterior não ser lido como
  deterioração permanente depois de uma mudança real de contexto.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import RoutineAlreadyExists, RoutineNotFound
from app.core.time import utc_now as _now
from app.models.routine import LifeEvent, Routine, RoutineEvent
from app.models.user import User


def _as_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def get_current_routine(db: Session, user: User) -> Routine:
    routine = db.scalar(
        select(Routine).where(Routine.user_id == user.id, Routine.period_end.is_(None))
    )
    if routine is None:
        raise RoutineNotFound(str(user.id))
    return routine


def create_routine(db: Session, user: User, data: dict) -> Routine:
    existing = db.scalar(select(Routine).where(Routine.user_id == user.id, Routine.period_end.is_(None)))
    if existing is not None:
        raise RoutineAlreadyExists(str(user.id))

    period_start = data.pop("period_start", None) or date.today()
    routine = Routine(user_id=user.id, version=1, period_start=period_start, **data)
    db.add(routine)
    db.commit()
    db.refresh(routine)
    return routine


def update_routine(db: Session, user: User, changes: dict) -> Routine:
    routine = get_current_routine(db, user)
    now = _now()
    for field, new_value in changes.items():
        old_value = getattr(routine, field)
        if old_value == new_value:
            continue
        db.add(
            RoutineEvent(
                routine_id=routine.id,
                changed_field=field,
                old_value=_as_text(old_value),
                new_value=_as_text(new_value),
                changed_at=now,
            )
        )
        setattr(routine, field, new_value)
    db.commit()
    db.refresh(routine)
    return routine


def start_new_version(db: Session, user: User, data: dict) -> Routine:
    """
    Fecha a versão atual (se existir) em `period_start` da nova, e
    cria a próxima — nunca deixa duas rotinas "abertas"
    simultaneamente (`period_end IS NULL`) para o mesmo usuário.
    """
    period_start = data.pop("period_start", None) or date.today()

    current = db.scalar(select(Routine).where(Routine.user_id == user.id, Routine.period_end.is_(None)))
    next_version = 1
    if current is not None:
        current.period_end = period_start
        next_version = current.version + 1

    routine = Routine(user_id=user.id, version=next_version, period_start=period_start, **data)
    db.add(routine)
    db.commit()
    db.refresh(routine)
    return routine


def list_routine_history(db: Session, user: User) -> list[Routine]:
    stmt = select(Routine).where(Routine.user_id == user.id).order_by(Routine.version.desc())
    return list(db.scalars(stmt))


def list_current_routine_events(db: Session, user: User) -> list[RoutineEvent]:
    routine = get_current_routine(db, user)
    stmt = select(RoutineEvent).where(RoutineEvent.routine_id == routine.id).order_by(RoutineEvent.changed_at)
    return list(db.scalars(stmt))


def create_life_event(db: Session, user: User, data: dict) -> LifeEvent:
    event = LifeEvent(user_id=user.id, **data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_life_events(db: Session, user: User) -> list[LifeEvent]:
    stmt = select(LifeEvent).where(LifeEvent.user_id == user.id).order_by(LifeEvent.start_date.desc())
    return list(db.scalars(stmt))
