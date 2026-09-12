"""
ETAPA 11 — item 6 do documento: check-in diário deliberadamente
curto, todo indicador opcional (quem está piorando tem menos
disposição pra preencher formulário longo). A única regra é "pelo
menos um campo preenchido" — um check-in inteiramente vazio não
carrega informação nenhuma e não deveria existir.
"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

_SCALE_FIELDS = (
    "mood",
    "energy",
    "anxiety",
    "ability_to_start_tasks",
    "willingness_to_interact",
    "sleep_quality",
    "sense_of_functioning",
)


class CheckInCreate(BaseModel):
    checkin_date: date | None = None  # None = hoje, no fuso horário do perfil

    mood: int | None = Field(default=None, ge=1, le=5)
    energy: int | None = Field(default=None, ge=1, le=5)
    anxiety: int | None = Field(default=None, ge=1, le=5)
    ability_to_start_tasks: int | None = Field(default=None, ge=1, le=5)
    willingness_to_interact: int | None = Field(default=None, ge=1, le=5)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    sense_of_functioning: int | None = Field(default=None, ge=1, le=5)
    extra_answers: dict | None = None

    @model_validator(mode="after")
    def at_least_one_field_filled(self):
        if all(getattr(self, field) is None for field in _SCALE_FIELDS) and not self.extra_answers:
            raise ValueError("preencha pelo menos um indicador do check-in")
        return self


class CheckInUpdate(BaseModel):
    """PATCH parcial — campo omitido não muda; não exige mínimo de campos (pode ser um ajuste único)."""
    mood: int | None = Field(default=None, ge=1, le=5)
    energy: int | None = Field(default=None, ge=1, le=5)
    anxiety: int | None = Field(default=None, ge=1, le=5)
    ability_to_start_tasks: int | None = Field(default=None, ge=1, le=5)
    willingness_to_interact: int | None = Field(default=None, ge=1, le=5)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    sense_of_functioning: int | None = Field(default=None, ge=1, le=5)
    extra_answers: dict | None = None


class CheckInPublic(BaseModel):
    id: uuid.UUID
    checkin_date: date

    mood: int | None
    energy: int | None
    anxiety: int | None
    ability_to_start_tasks: int | None
    willingness_to_interact: int | None
    sleep_quality: int | None
    sense_of_functioning: int | None
    extra_answers: dict | None

    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
