import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import MedicationNotFound, ScheduleNotFound
from app.models.user import User
from app.schemas.medication import (
    MedicationCreate,
    MedicationEventCreate,
    MedicationEventPublic,
    MedicationPublic,
    MedicationUpdate,
    ScheduleCreate,
    SchedulePublic,
    ScheduleUpdate,
)
from app.services import medication_service

router = APIRouter(prefix="/medications", tags=["medications"])


def _medication_not_found():
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="medicamento não encontrado")


def _schedule_not_found():
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="horário de medicamento não encontrado")


@router.post("", response_model=MedicationPublic, status_code=status.HTTP_201_CREATED)
def create_medication(
    payload: MedicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return medication_service.create_medication(db, current_user, payload.model_dump())


@router.get("", response_model=list[MedicationPublic])
def list_medications(
    include_discontinued: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return medication_service.list_medications(db, current_user, include_discontinued)


@router.get("/{medication_id}", response_model=MedicationPublic)
def get_medication(
    medication_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return medication_service.get_medication(db, current_user, medication_id)
    except MedicationNotFound:
        raise _medication_not_found()


@router.patch("/{medication_id}", response_model=MedicationPublic)
def update_medication(
    medication_id: uuid.UUID,
    payload: MedicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return medication_service.update_medication(
            db, current_user, medication_id, payload.model_dump(exclude_unset=True)
        )
    except MedicationNotFound:
        raise _medication_not_found()


@router.post("/{medication_id}/discontinue", response_model=MedicationPublic)
def discontinue_medication(
    medication_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return medication_service.discontinue_medication(db, current_user, medication_id)
    except MedicationNotFound:
        raise _medication_not_found()


@router.post("/{medication_id}/schedules", response_model=SchedulePublic, status_code=status.HTTP_201_CREATED)
def create_schedule(
    medication_id: uuid.UUID,
    payload: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return medication_service.create_schedule(db, current_user, medication_id, payload.model_dump())
    except MedicationNotFound:
        raise _medication_not_found()


@router.get("/{medication_id}/schedules", response_model=list[SchedulePublic])
def list_schedules(
    medication_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return medication_service.list_schedules(db, current_user, medication_id)
    except MedicationNotFound:
        raise _medication_not_found()


@router.patch("/{medication_id}/schedules/{schedule_id}", response_model=SchedulePublic)
def update_schedule(
    medication_id: uuid.UUID,
    schedule_id: uuid.UUID,
    payload: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return medication_service.update_schedule(
            db, current_user, medication_id, schedule_id, payload.model_dump(exclude_unset=True)
        )
    except MedicationNotFound:
        raise _medication_not_found()
    except ScheduleNotFound:
        raise _schedule_not_found()


@router.post(
    "/{medication_id}/schedules/{schedule_id}/events",
    response_model=MedicationEventPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    medication_id: uuid.UUID,
    schedule_id: uuid.UUID,
    payload: MedicationEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return medication_service.create_event(
            db, current_user, medication_id, schedule_id, payload.model_dump()
        )
    except MedicationNotFound:
        raise _medication_not_found()
    except ScheduleNotFound:
        raise _schedule_not_found()


@router.get("/{medication_id}/schedules/{schedule_id}/events", response_model=list[MedicationEventPublic])
def list_events_for_schedule(
    medication_id: uuid.UUID,
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return medication_service.list_events_for_schedule(db, current_user, medication_id, schedule_id)
    except MedicationNotFound:
        raise _medication_not_found()
    except ScheduleNotFound:
        raise _schedule_not_found()


@router.get("/{medication_id}/events", response_model=list[MedicationEventPublic])
def list_events_for_medication(
    medication_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return medication_service.list_events_for_medication(db, current_user, medication_id)
    except MedicationNotFound:
        raise _medication_not_found()
