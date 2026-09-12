import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import DeviationEventNotFound
from app.models.enums import DeviationEngine
from app.models.user import User
from app.schemas.deviation import DeviationEventPublic
from app.schemas.explainability import EngineExplanation
from app.services import deviation_service, explainability_service

router = APIRouter(prefix="/deviation", tags=["deviation"])


@router.post("/run", response_model=list[DeviationEventPublic])
def run_all_engines(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Roda os 4 motores (Executivo/Evitação/Ativação/Estabilidade) pra
    este usuário e devolve só os que encontraram desvio persistente.
    Disparado manualmente por enquanto — vira job noturno na ETAPA 22
    (ainda não existe scheduler).
    """
    return deviation_service.run_all_engines(db, current_user)


@router.post("/run/{engine}", response_model=DeviationEventPublic | None)
def run_single_engine(
    engine: DeviationEngine,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return deviation_service.run_engine(db, current_user, engine)


@router.get("/events", response_model=list[DeviationEventPublic])
def list_deviation_events(
    engine: DeviationEngine | None = None,
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return deviation_service.list_deviation_events(db, current_user, engine, limit)


@router.get("/events/{event_id}", response_model=DeviationEventPublic)
def get_deviation_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return deviation_service.get_deviation_event(db, current_user, event_id)
    except DeviationEventNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="evento de desvio não encontrado")


@router.get("/events/{event_id}/explanation", response_model=EngineExplanation)
def explain_deviation_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Item 15/22 — decompõe o evento por indicador: baseline vs. valor recente, dias seguidos."""
    try:
        event = deviation_service.get_deviation_event(db, current_user, event_id)
    except DeviationEventNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="evento de desvio não encontrado")
    return explainability_service.explain_deviation_event(event)
