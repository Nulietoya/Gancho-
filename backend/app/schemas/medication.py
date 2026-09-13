import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field, model_validator

from app.models.enums import MedicationEventStatus, MedicationSkipReason

# FORGOT_TO_CONFIRM é reservado pro futuro job automático (ETAPA 22 —
# quando a janela de confirmação expira sem resposta, o próprio
# sistema registra isso); não é um status que a pessoa escolhe.
_USER_SETTABLE_STATUSES = (
    MedicationEventStatus.TAKEN,
    MedicationEventStatus.NOT_TAKEN,
    MedicationEventStatus.SKIPPED_DELIBERATELY,
    MedicationEventStatus.UNAVAILABLE,
)


class MedicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    dosage_note: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    reminder_enabled: bool = True
    reminder_repeat_enabled: bool = False


class MedicationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    dosage_note: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    reminder_enabled: bool | None = None
    reminder_repeat_enabled: bool | None = None


class MedicationPublic(BaseModel):
    id: uuid.UUID
    name: str
    dosage_note: str | None
    notes: str | None
    reminder_enabled: bool
    reminder_repeat_enabled: bool
    discontinued_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduleCreate(BaseModel):
    time_of_day: time
    weekdays: list[int] | None = Field(default=None, description="0=segunda ... 6=domingo; omitido = todo dia")

    @model_validator(mode="after")
    def weekdays_in_range(self):
        if self.weekdays is not None and any(not (0 <= d <= 6) for d in self.weekdays):
            raise ValueError("weekdays deve conter apenas valores entre 0 (segunda) e 6 (domingo)")
        return self


class ScheduleUpdate(BaseModel):
    time_of_day: time | None = None
    weekdays: list[int] | None = None


class SchedulePublic(BaseModel):
    id: uuid.UUID
    medication_id: uuid.UUID
    time_of_day: time
    weekdays: list[int] | None

    model_config = {"from_attributes": True}


class MedicationEventCreate(BaseModel):
    """
    Item 13 — "registre apenas adesão conforme plano informado pelo
    usuário": isto nunca vira instrução de dose, só o fato de ter (ou
    não) tomado, e por quê.
    """
    scheduled_for: datetime
    status: MedicationEventStatus
    skip_reason: MedicationSkipReason | None = None
    custom_reason_text: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def status_and_reason_are_consistent(self):
        if self.status not in _USER_SETTABLE_STATUSES:
            raise ValueError(
                f"status '{self.status.value}' não pode ser registrado diretamente pela pessoa"
            )
        if self.status == MedicationEventStatus.TAKEN and self.skip_reason is not None:
            raise ValueError("'taken' não leva motivo de não-adesão")
        if self.status != MedicationEventStatus.TAKEN and self.skip_reason is None:
            raise ValueError("motivo obrigatório quando o status não é 'taken'")
        return self


class MedicationEventPublic(BaseModel):
    id: uuid.UUID
    schedule_id: uuid.UUID
    scheduled_for: datetime
    status: MedicationEventStatus
    skip_reason: MedicationSkipReason | None
    custom_reason_text: str | None
    confirmed_at: datetime | None

    model_config = {"from_attributes": True}
