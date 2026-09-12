"""ETAPA 21 — formas públicas de intervenções (microintervenção / body doubling)."""
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import InterventionStatus, InterventionType


class SuggestInterventionRequest(BaseModel):
    """
    `type` tem default MICROINTERVENTION porque é sempre a intervenção
    de menor atrito — o documento de referência (item 24) trata body
    doubling como o próximo degrau da escada, não o ponto de partida.
    Quem chama pede explicitamente BODY_DOUBLING_SESSION quando quer
    pular direto pra isso.
    """
    type: InterventionType = InterventionType.MICROINTERVENTION
    related_task_id: uuid.UUID | None = None
    related_deviation_id: uuid.UUID | None = None


class RequestInterventionRequest(BaseModel):
    """
    `support_relationship_id` só faz sentido pra BODY_DOUBLING_SESSION
    (quem a pessoa está pedindo pra ficar por perto) — omitido pra
    MICROINTERVENTION, que não envolve outra pessoa.
    """
    support_relationship_id: uuid.UUID | None = None


class InterventionResultInput(BaseModel):
    """Item 24/26: "ajudou ou não" é dado subjetivo do próprio usuário, nunca inferido."""
    helped: bool | None = None
    user_note: str | None = None


class InterventionPublic(BaseModel):
    id: uuid.UUID
    type: InterventionType
    status: InterventionStatus
    related_task_id: uuid.UUID | None
    related_deviation_id: uuid.UUID | None
    support_relationship_id: uuid.UUID | None
    suggestion_text: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InterventionResultPublic(BaseModel):
    id: uuid.UUID
    intervention_id: uuid.UUID
    helped: bool | None
    user_note: str | None
    recorded_at: datetime

    model_config = {"from_attributes": True}
