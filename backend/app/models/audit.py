import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import IdMixin
from app.models.enums import AuditAction


class AuditLog(IdMixin, Base):
    """
    Item 31. Append-only por convenção de uso (nenhuma rota de update
    ou delete é exposta para esta tabela). `target_user_id` é quem
    teve o próprio dado afetado — pode ser diferente de `actor_user_id`
    quando uma pessoa de confiança age sobre a conta do usuário
    (registrar observação, por exemplo). Nunca logar aqui o conteúdo
    do dado sensível em si (item 54: "nunca registrar inadvertidamente
    informações sensíveis em logs técnicos") — `metadata` guarda só o
    necessário para auditoria (ex.: qual campo, não o valor).
    """
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[AuditAction] = mapped_column(nullable=False, index=True)
    log_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
