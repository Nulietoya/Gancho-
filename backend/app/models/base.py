"""
Mixins comuns a todos os models.

- IdMixin: PK UUID (não sequencial — não vaza contagem de usuários/
  registros para quem inspeciona URLs ou IDs).
- TimestampMixin: created_at / updated_at em toda tabela, sempre
  gerados pelo banco (server_default / server_onupdate), nunca
  confiando no relógio da aplicação.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
