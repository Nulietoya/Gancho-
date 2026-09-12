import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import TaskEventType, TaskFailureReasonType, TaskOrigin, TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=80)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None
    estimated_minutes: int | None = Field(default=None, gt=0)


class TaskUpdate(BaseModel):
    """
    PATCH parcial dos campos descritivos — nunca do `status`, que só
    muda através dos endpoints de ação (start/pause/postpone/...) para
    garantir que toda mudança de estado gere o `TaskEvent`
    correspondente (item 33).
    """
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=80)
    priority: TaskPriority | None = None
    due_date: date | None = None
    estimated_minutes: int | None = Field(default=None, gt=0)


class TaskFailureReasonInput(BaseModel):
    """Usado ao adiar ou cancelar — item 8: motivo de não-conclusão."""
    reason: TaskFailureReasonType
    custom_text: str | None = Field(default=None, max_length=500)


class TaskPublic(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    category: str | None
    priority: TaskPriority
    status: TaskStatus

    due_date: date | None
    estimated_minutes: int | None
    actual_minutes: int | None

    started_at: datetime | None
    completed_at: datetime | None

    postponed_count: int
    attempt_count: int

    origin: TaskOrigin
    source_relationship_id: uuid.UUID | None
    support_relationship_id: uuid.UUID | None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskEventPublic(BaseModel):
    id: uuid.UUID
    event_type: TaskEventType
    occurred_at: datetime
    event_metadata: dict | None

    model_config = {"from_attributes": True}


class SuggestTaskRequest(BaseModel):
    """Item 24 (nível de permissão 2 — 'Apoiar'): pessoa de confiança sugere uma tarefa."""
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_date: date | None = None
