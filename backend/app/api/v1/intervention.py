"""
ETAPA 21 — rotas de intervenções (microintervenção / body doubling).
A rota de "aceitar" um pedido de body doubling, feita pela pessoa de
confiança, mora em `trusted_people.py` (mesmo critério já usado pra
`suggest_task`/`create_observation`: toda ação de uma pessoa de
confiança sobre a conta de outra pessoa fica junto das outras rotas
que dependem de `require_relationship_permission`).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import (
    DeviationEventNotFound,
    InterventionNotFound,
    InvalidInterventionTransition,
    RelationshipNotFound,
    TaskNotFound,
)
from app.models.enums import InterventionStatus
from app.models.user import User
from app.schemas.intervention import (
    InterventionPublic,
    InterventionResultInput,
    InterventionResultPublic,
    RequestInterventionRequest,
    SuggestInterventionRequest,
)
from app.services import intervention_service

router = APIRouter(prefix="/interventions", tags=["interventions"])


def _handle(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except InterventionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="intervenção não encontrada")
    except InvalidInterventionTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
    except RelationshipNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="relacionamento não encontrado")


@router.post("/suggest", response_model=InterventionPublic, status_code=status.HTTP_201_CREATED)
def suggest_intervention(
    payload: SuggestInterventionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return intervention_service.suggest_intervention(
            db,
            current_user,
            type=payload.type,
            related_task_id=payload.related_task_id,
            related_deviation_id=payload.related_deviation_id,
        )
    except TaskNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="tarefa relacionada não encontrada")
    except DeviationEventNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="evento de desvio relacionado não encontrado")


@router.get("", response_model=list[InterventionPublic])
def list_interventions(
    status_filter: InterventionStatus | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return intervention_service.list_interventions(db, current_user, status_filter)


@router.get("/{intervention_id}", response_model=InterventionPublic)
def get_intervention(
    intervention_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _handle(intervention_service.get_intervention, db, current_user, intervention_id)


@router.post("/{intervention_id}/request", response_model=InterventionPublic)
def request_intervention(
    intervention_id: uuid.UUID,
    payload: RequestInterventionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _handle(
        intervention_service.request_intervention,
        db,
        current_user,
        intervention_id,
        payload.support_relationship_id,
    )


@router.post("/{intervention_id}/start", response_model=InterventionPublic)
def start_intervention(
    intervention_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _handle(intervention_service.start_intervention, db, current_user, intervention_id)


@router.post("/{intervention_id}/finish", response_model=InterventionPublic)
def finish_intervention(
    intervention_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _handle(intervention_service.finish_intervention, db, current_user, intervention_id)


@router.post("/{intervention_id}/dismiss", response_model=InterventionPublic)
def dismiss_intervention(
    intervention_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _handle(intervention_service.dismiss_intervention, db, current_user, intervention_id)


@router.put("/{intervention_id}/result", response_model=InterventionResultPublic)
def record_result(
    intervention_id: uuid.UUID,
    payload: InterventionResultInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _handle(
        intervention_service.record_result,
        db,
        current_user,
        intervention_id,
        payload.helped,
        payload.user_note,
    )
