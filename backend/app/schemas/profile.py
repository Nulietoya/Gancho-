"""
ETAPA 8 (perfil) + 9 (onboarding guiado). O onboarding é, na prática,
o preenchimento progressivo destes mesmos campos — não existe uma
tabela separada de "respostas de onboarding": item 4 do documento de
referência pede contexto individual reutilizável depois (perfil), não
um questionário descartável.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ToneStyle


class ProfileCreate(BaseModel):
    """
    Cria o perfil (uma vez por usuário — é 1:1). `display_name` é o
    único campo realmente obrigatório; todo o resto é texto livre que
    a pessoa pode não ter para preencher ainda (ex.: "dificuldades
    recorrentes" pode legitimamente ficar vazio) e completar depois
    via PATCH.
    """
    display_name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default="America/Sao_Paulo", max_length=64)
    tone_preference: ToneStyle = ToneStyle.COMPANHEIRO_CALMO

    main_responsibilities: str | None = None
    work_or_study: str | None = None
    habits: str | None = None
    patterns_considered_normal: str | None = None
    recurring_difficulties: str | None = None
    self_recognized_warning_signs: list[str] | None = None
    privacy_preferences: dict | None = None


class ProfileUpdate(BaseModel):
    """
    Todos os campos opcionais — PATCH parcial. `None` num campo
    significa "não mudar", não "apagar" (ver `EXPLICIT_UNSET` em
    profile_service.update_profile: usamos `exclude_unset` no
    schema para diferenciar "campo omitido" de "campo enviado como
    null" quando isso importar).
    """
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    tone_preference: ToneStyle | None = None

    main_responsibilities: str | None = None
    work_or_study: str | None = None
    habits: str | None = None
    patterns_considered_normal: str | None = None
    recurring_difficulties: str | None = None
    self_recognized_warning_signs: list[str] | None = None
    privacy_preferences: dict | None = None


class ProfilePublic(BaseModel):
    id: uuid.UUID
    display_name: str
    timezone: str
    tone_preference: ToneStyle

    main_responsibilities: str | None
    work_or_study: str | None
    habits: str | None
    patterns_considered_normal: str | None
    recurring_difficulties: str | None
    self_recognized_warning_signs: list[str] | None
    privacy_preferences: dict | None

    onboarding_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
