"""
ETAPA 25 (item 19) — "Plano quando eu não perceber", estilo WRAP
(Wellness Recovery Action Plan): escrito pelo próprio usuário durante
período estável, nunca gerado ou sugerido pelo sistema. `threshold_description`
é sempre texto livre da própria pessoa ("faltei 2 dias seguidos ao
trabalho") — nunca um número ou regra que o sistema infere sozinho,
mesmo espírito de "nunca inventar limiar clínico" já usado no motor
de desvio (ETAPA 18) e no modelo de estado (ETAPA 19).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PersonalPlanSignal


class PersonalPlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1)


class PersonalPlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, min_length=1)


class PersonalPlanRuleCreate(BaseModel):
    signal_key: PersonalPlanSignal
    threshold_description: str = Field(min_length=1)


class PersonalPlanRuleUpdate(BaseModel):
    threshold_description: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class PersonalPlanRulePublic(BaseModel):
    id: uuid.UUID
    signal_key: PersonalPlanSignal
    threshold_description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonalPlanPublic(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    is_active: bool
    rules: list[PersonalPlanRulePublic]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
