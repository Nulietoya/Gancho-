from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import RoutineAlreadyExists, RoutineNotFound
from app.models.user import User
from app.schemas.routine import (
    LifeEventCreate,
    LifeEventPublic,
    RoutineCreate,
    RoutineEventPublic,
    RoutinePublic,
    RoutineUpdate,
)
from app.services import routine_service

router = APIRouter(prefix="/routines", tags=["routines"])
life_events_router = APIRouter(prefix="/life-events", tags=["life-events"])


def _not_found():
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="nenhuma rotina de referência declarada ainda")


@router.post("", response_model=RoutinePublic, status_code=status.HTTP_201_CREATED)
def create_routine(
    payload: RoutineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return routine_service.create_routine(db, current_user, payload.model_dump(exclude_unset=True))
    except RoutineAlreadyExists:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="já existe uma rotina ativa — use PATCH pra ajustar ou /new-version pra uma virada de vida",
        )


@router.get("/current", response_model=RoutinePublic)
def get_current_routine(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return routine_service.get_current_routine(db, current_user)
    except RoutineNotFound:
        raise _not_found()


@router.patch("/current", response_model=RoutinePublic)
def update_routine(
    payload: RoutineUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return routine_service.update_routine(db, current_user, payload.model_dump(exclude_unset=True))
    except RoutineNotFound:
        raise _not_found()


@router.get("/current/events", response_model=list[RoutineEventPublic])
def list_current_routine_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return routine_service.list_current_routine_events(db, current_user)
    except RoutineNotFound:
        raise _not_found()


@router.post("/new-version", response_model=RoutinePublic, status_code=status.HTTP_201_CREATED)
def start_new_version(
    payload: RoutineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Item 56/57 — virada de vida: fecha a rotina atual (se existir) e
    declara uma nova do zero, pra um desvio contra o baseline antigo
    não ser lido como deterioração depois de uma mudança real de
    contexto (novo emprego, mudança de cidade etc.).
    """
    return routine_service.start_new_version(db, current_user, payload.model_dump(exclude_unset=True))


@router.get("", response_model=list[RoutinePublic])
def list_routine_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return routine_service.list_routine_history(db, current_user)


@life_events_router.post("", response_model=LifeEventPublic, status_code=status.HTTP_201_CREATED)
def create_life_event(
    payload: LifeEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return routine_service.create_life_event(db, current_user, payload.model_dump())


@life_events_router.get("", response_model=list[LifeEventPublic])
def list_life_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return routine_service.list_life_events(db, current_user)
