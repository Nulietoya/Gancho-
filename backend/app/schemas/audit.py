"""ETAPA 26 (item 31) — consulta da trilha de auditoria da própria conta."""
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AuditAction


class AuditLogEntry(BaseModel):
    """
    Nunca expõe o id de quem foi o ator quando não é o próprio dono
    (`actor_is_self=False` cobre "uma pessoa de confiança ou o sistema
    fez algo relacionado à minha conta" sem revelar qual delas — cruzar
    isso com a lista de relacionamentos é decisão de UI, ETAPA 27).
    `metadata` nunca contém dado sensível em si (item 54 — já garantido
    por quem grava cada `AuditLog`, aqui só repassa o que já está lá).
    """
    id: uuid.UUID
    action: AuditAction
    actor_is_self: bool
    metadata: dict | None
    created_at: datetime
