import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.models.enums import ActivationDomain, LifeEventType


class RoutineCreate(BaseModel):
    """
    Item 4/11 — "como é o seu dia quando você está bem", declarado no
    onboarding. `period_start` default é hoje; todo o resto é
    opcional (a pessoa pode não saber/não querer declarar tudo de
    uma vez, mesmo raciocínio do `Profile`).
    """
    period_start: date | None = None
    typical_wake_time: time | None = None
    typical_sleep_time: time | None = None
    goes_out_on_weekdays: bool | None = None
    social_contact_days_per_week: int | None = Field(default=None, ge=0, le=7)
    typical_tasks_postponed_on_good_day: int | None = Field(default=None, ge=0)
    selected_activation_domains: list[ActivationDomain] | None = None
    notes: str | None = None

    # `use_enum_values` grava a string do enum (não o objeto Enum) já
    # na validação — evita que `model_dump()` devolva membros de
    # `ActivationDomain` que o service compararia/gravaria como
    # objeto Python em vez do texto que a coluna `ARRAY(String)` espera.
    model_config = {"use_enum_values": True}


class RoutineUpdate(BaseModel):
    """
    PATCH da versão atual — edição corriqueira (ajustar um horário,
    corrigir um campo), não uma virada de vida. Cada campo alterado
    gera um `RoutineEvent`; `version`/`period_start`/`period_end`
    nunca mudam aqui (ver `POST /routines/new-version` pra isso).
    """
    typical_wake_time: time | None = None
    typical_sleep_time: time | None = None
    goes_out_on_weekdays: bool | None = None
    social_contact_days_per_week: int | None = Field(default=None, ge=0, le=7)
    typical_tasks_postponed_on_good_day: int | None = Field(default=None, ge=0)
    selected_activation_domains: list[ActivationDomain] | None = None
    notes: str | None = None

    model_config = {"use_enum_values": True}


class RoutinePublic(BaseModel):
    id: uuid.UUID
    version: int
    period_start: date
    period_end: date | None

    typical_wake_time: time | None
    typical_sleep_time: time | None
    goes_out_on_weekdays: bool | None
    social_contact_days_per_week: int | None
    typical_tasks_postponed_on_good_day: int | None
    selected_activation_domains: list[str] | None
    notes: str | None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoutineEventPublic(BaseModel):
    id: uuid.UUID
    changed_field: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime

    model_config = {"from_attributes": True}


class LifeEventCreate(BaseModel):
    """Item 57 — contexto pra não confundir transição de vida com deterioração."""
    event_type: LifeEventType
    description: str | None = Field(default=None, max_length=500)
    start_date: date
    end_date: date | None = None


class LifeEventPublic(BaseModel):
    id: uuid.UUID
    event_type: LifeEventType
    description: str | None
    start_date: date
    end_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}
