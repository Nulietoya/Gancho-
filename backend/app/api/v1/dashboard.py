"""ETAPA 23/24 — rotas de dashboard do dono da conta."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.dashboard import AnalyticsDashboard, DailyDashboard
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/daily", response_model=DailyDashboard)
def get_daily_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return dashboard_service.build_daily_dashboard(db, current_user)


@router.get("/analytics", response_model=AnalyticsDashboard)
def get_analytics_dashboard(
    days: int = Query(default=30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return dashboard_service.build_analytics_dashboard(db, current_user, days=days)
