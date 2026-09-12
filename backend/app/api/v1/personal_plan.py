"""ETAPA 25 (item 19) — rotas do plano pessoal ("plano quando eu não perceber")."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import PersonalPlanAlreadyExists, PersonalPlanNotFound, PersonalPlanRuleNotFound
from app.models.user import User
from app.schemas.personal_plan import (
    PersonalPlanCreate,
    PersonalPlanPublic,
    PersonalPlanRuleCreate,
    PersonalPlanRulePublic,
    PersonalPlanRuleUpdate,
    PersonalPlanUpdate,
)
from app.services import personal_plan_service

router = APIRouter(prefix="/personal-plan", tags=["personal-plan"])


def _not_found():
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="nenhum plano ativo — crie um primeiro")


@router.post("", response_model=PersonalPlanPublic, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PersonalPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return personal_plan_service.create_plan(db, current_user, payload.model_dump())
    except PersonalPlanAlreadyExists:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="já existe um plano ativo — edite-o (PATCH) ou desative-o antes de criar outro",
        )


@router.get("", response_model=PersonalPlanPublic)
def get_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return personal_plan_service.get_active_plan(db, current_user.id)
    except PersonalPlanNotFound:
        raise _not_found()


@router.patch("", response_model=PersonalPlanPublic)
def update_plan(
    payload: PersonalPlanUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return personal_plan_service.update_plan(db, current_user, payload.model_dump(exclude_unset=True))
    except PersonalPlanNotFound:
        raise _not_found()


@router.post("/deactivate", response_model=PersonalPlanPublic)
def deactivate_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return personal_plan_service.deactivate_plan(db, current_user)
    except PersonalPlanNotFound:
        raise _not_found()


@router.post("/rules", response_model=PersonalPlanRulePublic, status_code=status.HTTP_201_CREATED)
def add_rule(
    payload: PersonalPlanRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return personal_plan_service.add_rule(db, current_user, payload.signal_key, payload.threshold_description)
    except PersonalPlanNotFound:
        raise _not_found()


@router.patch("/rules/{rule_id}", response_model=PersonalPlanRulePublic)
def update_rule(
    rule_id: uuid.UUID,
    payload: PersonalPlanRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return personal_plan_service.update_rule(db, current_user, rule_id, payload.model_dump(exclude_unset=True))
    except PersonalPlanRuleNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="regra não encontrada")
