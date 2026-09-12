"""
ETAPA 18 — saída do motor de desvio. Só leitura pela API além do
disparo (`POST /deviation/run*`); a detecção em si roda inteira no
service, aqui é só a forma pública de `DeviationEvent`.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DeviationEngine


class DeviationEventPublic(BaseModel):
    id: uuid.UUID
    engine: DeviationEngine
    detected_at: datetime
    magnitude: float
    duration_days: int
    domains_count: int
    convergence_score: float | None
    triggering_indicator_keys: list[str]
    baseline_snapshot: dict
    explanation: str

    model_config = {"from_attributes": True}
