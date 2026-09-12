from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import ProfileAlreadyExists, ProfileNotFound
from app.models.user import User
from app.schemas.profile import ProfileCreate, ProfilePublic, ProfileUpdate
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("", response_model=ProfilePublic, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return profile_service.create_profile(db, current_user, payload.model_dump())
    except ProfileAlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="perfil já existe para este usuário")


@router.get("", response_model=ProfilePublic)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return profile_service.get_profile(db, current_user)
    except ProfileNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="perfil ainda não criado — conclua o onboarding primeiro",
        )


@router.patch("", response_model=ProfilePublic)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return profile_service.update_profile(db, current_user, payload.model_dump(exclude_unset=True))
    except ProfileNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="perfil ainda não criado — conclua o onboarding primeiro",
        )


@router.post("/complete-onboarding", response_model=ProfilePublic)
def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Item 4 (onboarding guiado — ETAPA 9): confirmação explícita de que
    a etapa inicial terminou. Idempotente — chamar de novo não é erro.
    """
    try:
        return profile_service.complete_onboarding(db, current_user)
    except ProfileNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="perfil ainda não criado — conclua o onboarding primeiro",
        )
