"""
Regras de negócio de tarefas e eventos de tarefa (ETAPA 10 — itens
7/8/9/24/25/33 do documento de referência). Nenhuma rota altera
`Task.status` diretamente: toda transição passa por uma função de
ação daqui, que grava o `TaskEvent` imutável correspondente e só
então atualiza os campos desnormalizados (`status`, contadores,
timestamps) — a mesma separação "evento é a fonte de verdade, coluna
é cache de leitura" já usada em `TaskEvent`/`RoutineEvent`/`Alert`.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidTaskTransition, TaskNotFound
from app.core.time import utc_now as _now
from app.models.enums import TaskEventType, TaskFailureReasonType, TaskOrigin, TaskStatus
from app.models.task import Task, TaskEvent, TaskFailureReason
from app.models.user import User
from app.services import indicator_service

# De quais status cada ação pode partir. Terminal (COMPLETED/CANCELLED)
# nunca aparece como origem — uma tarefa terminada não reabre; se a
# pessoa quer retomar, cria uma nova (mantém o histórico honesto).
_ALLOWED_FROM = {
    "start": {TaskStatus.PENDING, TaskStatus.POSTPONED},
    "resume": {TaskStatus.PAUSED},
    "pause": {TaskStatus.STARTED},
    "postpone": {TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PAUSED},
    "complete": {TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PAUSED, TaskStatus.POSTPONED},
    "cancel": {TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PAUSED, TaskStatus.POSTPONED},
}


def create_task(
    db: Session,
    owner_user_id: uuid.UUID,
    data: dict,
    *,
    origin: TaskOrigin = TaskOrigin.SELF,
    source_relationship_id: uuid.UUID | None = None,
) -> Task:
    task = Task(
        user_id=owner_user_id,
        origin=origin,
        source_relationship_id=source_relationship_id,
        **data,
    )
    db.add(task)
    db.flush()  # garante task.id antes de gravar o evento
    _record_event(db, task, TaskEventType.CREATED)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, user: User, task_id: uuid.UUID) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if task is None:
        raise TaskNotFound(str(task_id))
    return task


def list_tasks(db: Session, user: User, status_filter: TaskStatus | None = None) -> list[Task]:
    stmt = select(Task).where(Task.user_id == user.id).order_by(Task.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter)
    return list(db.scalars(stmt))


def update_task(db: Session, user: User, task_id: uuid.UUID, changes: dict) -> Task:
    task = get_task(db, user, task_id)
    for field, value in changes.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def list_events(db: Session, user: User, task_id: uuid.UUID) -> list[TaskEvent]:
    get_task(db, user, task_id)  # valida posse antes de expor histórico
    stmt = select(TaskEvent).where(TaskEvent.task_id == task_id).order_by(TaskEvent.occurred_at)
    return list(db.scalars(stmt))


def _record_event(db: Session, task: Task, event_type: TaskEventType, metadata: dict | None = None) -> TaskEvent:
    event = TaskEvent(task_id=task.id, event_type=event_type, occurred_at=_now(), event_metadata=metadata)
    db.add(event)
    db.flush()
    return event


_EVENT_TYPE_FOR_ACTION = {
    "start": TaskEventType.STARTED,
    "resume": TaskEventType.RESUMED,
    "pause": TaskEventType.PAUSED,
    "postpone": TaskEventType.POSTPONED,
    "complete": TaskEventType.COMPLETED,
    "cancel": TaskEventType.CANCELLED,
}


def _transition(db: Session, user: User, task_id: uuid.UUID, action: str) -> tuple[Task, TaskEvent]:
    task = get_task(db, user, task_id)
    if task.status not in _ALLOWED_FROM[action]:
        raise InvalidTaskTransition(task.status.value, action)
    event = _record_event(db, task, _EVENT_TYPE_FOR_ACTION[action])
    # ETAPA 17: STARTED/POSTPONED/COMPLETED alimentam FunctionalIndicator
    # (recalculado do zero a partir do TaskEvent, nunca incrementado).
    indicator_service.sync_task_event_indicators(db, task.user_id, event.occurred_at.date())
    return task, event


def start_task(db: Session, user: User, task_id: uuid.UUID) -> Task:
    task, _event = _transition(db, user, task_id, "start")
    task.status = TaskStatus.STARTED
    if task.started_at is None:
        task.started_at = _now()
    task.attempt_count += 1
    db.commit()
    db.refresh(task)
    return task


def resume_task(db: Session, user: User, task_id: uuid.UUID) -> Task:
    task, _event = _transition(db, user, task_id, "resume")
    task.status = TaskStatus.STARTED
    task.attempt_count += 1
    db.commit()
    db.refresh(task)
    return task


def pause_task(db: Session, user: User, task_id: uuid.UUID) -> Task:
    task, _event = _transition(db, user, task_id, "pause")
    task.status = TaskStatus.PAUSED
    db.commit()
    db.refresh(task)
    return task


def postpone_task(
    db: Session,
    user: User,
    task_id: uuid.UUID,
    reason: TaskFailureReasonType,
    custom_text: str | None = None,
) -> Task:
    task, event = _transition(db, user, task_id, "postpone")
    task.status = TaskStatus.POSTPONED
    task.postponed_count += 1
    db.add(TaskFailureReason(task_id=task.id, event_id=event.id, reason=reason, custom_text=custom_text, recorded_at=_now()))
    db.commit()
    db.refresh(task)
    return task


def complete_task(db: Session, user: User, task_id: uuid.UUID) -> Task:
    task, _event = _transition(db, user, task_id, "complete")
    task.status = TaskStatus.COMPLETED
    task.completed_at = _now()
    db.commit()
    db.refresh(task)
    return task


def cancel_task(
    db: Session,
    user: User,
    task_id: uuid.UUID,
    reason: TaskFailureReasonType | None = None,
    custom_text: str | None = None,
) -> Task:
    task, event = _transition(db, user, task_id, "cancel")
    task.status = TaskStatus.CANCELLED
    if reason is not None:
        db.add(TaskFailureReason(task_id=task.id, event_id=event.id, reason=reason, custom_text=custom_text, recorded_at=_now()))
    db.commit()
    db.refresh(task)
    return task
