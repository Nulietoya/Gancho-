"""ETAPA 19 — forma pública de `Alert` (o estado verde/amarelo/vermelho)."""
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AlertState


class AlertPublic(BaseModel):
    id: uuid.UUID
    state: AlertState
    triggering_deviation_id: uuid.UUID | None
    reason_summary: str
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
