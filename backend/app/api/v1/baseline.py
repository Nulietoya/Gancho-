from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import BaselineNotFound, NoIndicatorData
from app.models.enums import IndicatorKey
from app.models.user import User
from app.schemas.baseline import (
    BaselinePublic,
    BaselineVersionPublic,
    FunctionalIndicatorPublic,
    RecomputeRequest,
)
from app.services import baseline_service, indicator_service

router = APIRouter(prefix="/baseline", tags=["baseline"])
indicators_router = APIRouter(prefix="/indicators", tags=["indicators"])


def _not_found():
    return HTTPException(
        status.HTTP_404_NOT_FOUND,
        detail="nenhum baseline ativo pra este indicador ainda — calcule com /recompute primeiro",
    )


@router.get("", response_model=list[BaselinePublic])
def list_active_baselines(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    baselines = baseline_service.list_active_baselines(db, current_user)
    return [BaselinePublic.from_baseline(b) for b in baselines]


@router.get("/{indicator_key}", response_model=BaselinePublic)
def get_baseline(
    indicator_key: IndicatorKey,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        baseline = baseline_service.get_active_baseline(db, current_user, indicator_key)
    except BaselineNotFound:
        raise _not_found()
    return BaselinePublic.from_baseline(baseline)


@router.get("/{indicator_key}/history", response_model=list[BaselineVersionPublic])
def get_baseline_history(
    indicator_key: IndicatorKey,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return baseline_service.get_baseline_history(db, current_user, indicator_key)


@router.post("/{indicator_key}/recompute", response_model=BaselinePublic)
def recompute_baseline(
    indicator_key: IndicatorKey,
    payload: RecomputeRequest = RecomputeRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Item 5 — recalcula os números dentro da mesma versão (sobe um
    `BaselineMetric` novo). Cria a versão 1 na primeira chamada, se
    ainda não existir nenhuma.
    """
    try:
        baseline = baseline_service.recompute_baseline(db, current_user, indicator_key, payload.window_days)
    except NoIndicatorData:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="nenhum dado registrado pra este indicador na janela pedida",
        )
    return BaselinePublic.from_baseline(baseline)


@router.post("/{indicator_key}/recalibrate", response_model=BaselinePublic)
def recalibrate_baseline(
    indicator_key: IndicatorKey,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Item 56/57 — virada de vida: fecha a versão atual e abre outra do zero."""
    baseline = baseline_service.recalibrate_baseline(db, current_user, indicator_key)
    return BaselinePublic.from_baseline(baseline)


@indicators_router.get("", response_model=list[FunctionalIndicatorPublic])
def list_indicator_values(
    indicator_key: IndicatorKey | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 90,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Leitura direta do fato normalizado — item 38/transparência: a
    pessoa pode ver exatamente o que alimenta o próprio baseline.
    """
    return indicator_service.list_indicator_values(db, current_user.id, indicator_key, date_from, date_to, limit)
