import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import AlertNotFound
from app.models.user import User
from app.schemas.alert import AlertPublic
from app.schemas.explainability import AlertExplanation
from app.services import alert_service, explainability_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/sync", response_model=AlertPublic)
def sync_alert_state(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reavalia o estado (VERDE/AMARELO/VERMELHO) a partir dos
    `DeviationEvent`s recentes dos 4 motores. Só cria uma linha nova
    em `Alert` quando o estado muda; devolve o atual sem duplicar
    quando não muda. Disparado manualmente por enquanto — vira job
    noturno na ETAPA 22, junto de `POST /deviation/run`.
    """
    return alert_service.sync_alert_state(db, current_user)


@router.get("/current", response_model=AlertPublic)
def get_current_alert(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert = alert_service.get_current_alert(db, current_user)
    if alert is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="nenhum estado calculado ainda — chame /alerts/sync primeiro",
        )
    return alert


@router.get("", response_model=list[AlertPublic])
def list_alert_history(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return alert_service.list_alert_history(db, current_user, limit)


@router.post("/{alert_id}/acknowledge", response_model=AlertPublic)
def acknowledge_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return alert_service.acknowledge_alert(db, current_user, alert_id)
    except AlertNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="alerta não encontrado")


@router.post("/{alert_id}/resolve", response_model=AlertPublic)
def resolve_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return alert_service.resolve_alert(db, current_user, alert_id)
    except AlertNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="alerta não encontrado")


@router.get("/{alert_id}/explanation", response_model=AlertExplanation)
def explain_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Item 15/22 — por quê o estado é esse: quais motores convergiram
    (dentro da janela de relevância atual) e, por motor, quais
    indicadores mudaram, comparando com o baseline de cada um.
    """
    try:
        alert = alert_service.get_alert(db, current_user, alert_id)
    except AlertNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="alerta não encontrado")
    return explainability_service.explain_alert(db, current_user, alert)
