"""ETAPA 22 — leitura/gestão de notificações e preferências (item 37)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import NotificationNotFound
from app.models.user import User
from app.schemas.notification import (
    NotificationPreferencePublic,
    NotificationPreferenceUpdate,
    NotificationPublic,
)
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationPublic])
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return notification_service.list_notifications(db, current_user, unread_only, limit)


@router.post("/{notification_id}/read", response_model=NotificationPublic)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return notification_service.mark_read(db, current_user, notification_id)
    except NotificationNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="notificação não encontrada")


@router.get("/preferences", response_model=NotificationPreferencePublic)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return notification_service.get_or_create_preferences(db, current_user.id)


@router.put("/preferences", response_model=NotificationPreferencePublic)
def update_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return notification_service.update_preferences(db, current_user.id, payload.model_dump(exclude_unset=True))
