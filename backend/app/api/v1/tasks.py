import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import InvalidTaskTransition, TaskNotFound
from app.models.enums import TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskEventPublic, TaskFailureReasonInput, TaskPublic, TaskUpdate
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _not_found():
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="tarefa não encontrada")


def _invalid_transition(exc: InvalidTaskTransition):
    return HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("", response_model=TaskPublic, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return task_service.create_task(db, current_user.id, payload.model_dump())


@router.get("", response_model=list[TaskPublic])
def list_tasks(
    status_filter: TaskStatus | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return task_service.list_tasks(db, current_user, status_filter)


@router.get("/{task_id}", response_model=TaskPublic)
def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return task_service.get_task(db, current_user, task_id)
    except TaskNotFound:
        raise _not_found()


@router.patch("/{task_id}", response_model=TaskPublic)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return task_service.update_task(db, current_user, task_id, payload.model_dump(exclude_unset=True))
    except TaskNotFound:
        raise _not_found()


@router.get("/{task_id}/events", response_model=list[TaskEventPublic])
def list_task_events(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return task_service.list_events(db, current_user, task_id)
    except TaskNotFound:
        raise _not_found()


@router.post("/{task_id}/start", response_model=TaskPublic)
def start_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return task_service.start_task(db, current_user, task_id)
    except TaskNotFound:
        raise _not_found()
    except InvalidTaskTransition as exc:
        raise _invalid_transition(exc)


@router.post("/{task_id}/resume", response_model=TaskPublic)
def resume_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return task_service.resume_task(db, current_user, task_id)
    except TaskNotFound:
        raise _not_found()
    except InvalidTaskTransition as exc:
        raise _invalid_transition(exc)


@router.post("/{task_id}/pause", response_model=TaskPublic)
def pause_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return task_service.pause_task(db, current_user, task_id)
    except TaskNotFound:
        raise _not_found()
    except InvalidTaskTransition as exc:
        raise _invalid_transition(exc)


@router.post("/{task_id}/postpone", response_model=TaskPublic)
def postpone_task(
    task_id: uuid.UUID,
    payload: TaskFailureReasonInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Item 8: adiar sempre pede o motivo — nunca fica implícito no silêncio."""
    try:
        return task_service.postpone_task(db, current_user, task_id, payload.reason, payload.custom_text)
    except TaskNotFound:
        raise _not_found()
    except InvalidTaskTransition as exc:
        raise _invalid_transition(exc)


@router.post("/{task_id}/complete", response_model=TaskPublic)
def complete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return task_service.complete_task(db, current_user, task_id)
    except TaskNotFound:
        raise _not_found()
    except InvalidTaskTransition as exc:
        raise _invalid_transition(exc)


@router.post("/{task_id}/cancel", response_model=TaskPublic)
def cancel_task(
    task_id: uuid.UUID,
    payload: TaskFailureReasonInput | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Motivo é opcional ao cancelar (a tarefa pode ter deixado de fazer sentido, não ter sido evitada)."""
    try:
        reason = payload.reason if payload else None
        custom_text = payload.custom_text if payload else None
        return task_service.cancel_task(db, current_user, task_id, reason, custom_text)
    except TaskNotFound:
        raise _not_found()
    except InvalidTaskTransition as exc:
        raise _invalid_transition(exc)
