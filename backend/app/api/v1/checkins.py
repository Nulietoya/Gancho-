from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import CheckInAlreadyExists, CheckInNotFound
from app.models.user import User
from app.schemas.checkin import CheckInCreate, CheckInPublic, CheckInUpdate
from app.services import checkin_service

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.post("", response_model=CheckInPublic, status_code=status.HTTP_201_CREATED)
def create_checkin(
    payload: CheckInCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return checkin_service.create_checkin(db, current_user, payload.model_dump())
    except CheckInAlreadyExists:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="já existe um check-in para esta data — use PATCH pra revisar",
        )


@router.get("", response_model=list[CheckInPublic])
def list_checkins(
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return checkin_service.list_checkins(db, current_user, date_from, date_to, limit)


@router.get("/{checkin_date}", response_model=CheckInPublic)
def get_checkin(
    checkin_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return checkin_service.get_checkin(db, current_user, checkin_date)
    except CheckInNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="nenhum check-in registrado nesta data")


@router.patch("/{checkin_date}", response_model=CheckInPublic)
def update_checkin(
    checkin_date: date,
    payload: CheckInUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return checkin_service.update_checkin(db, current_user, checkin_date, payload.model_dump(exclude_unset=True))
    except CheckInNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="nenhum check-in registrado nesta data")
