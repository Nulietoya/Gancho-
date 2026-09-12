import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import IdMixin


class RefreshSession(IdMixin, Base):
    """
    Item 35: sessões, expiração, revogação. Guarda só o HASH do
    refresh token (nunca o valor em claro — item 30 "proteção de
    credenciais") — se o banco vazar, os tokens em si continuam
    inúteis. Usado SHA-256 em vez de Argon2 aqui de propósito: o
    token já nasce com entropia alta (gerado por
    secrets.token_urlsafe), então não precisa de uma função lenta
    contra força bruta como uma senha humana precisa — só precisa de
    um hash não reversível para o caso de vazamento do banco.

    Revogação (logout, troca de senha, reset de senha) marca
    `revoked_at` — nunca apaga a linha, pra manter rastro auditável de
    sessões encerradas.
    """
    __tablename__ = "refresh_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PasswordResetToken(IdMixin, Base):
    """
    Item 35: recuperação de senha. Mesma lógica de hash do
    RefreshSession. `used_at` impede reuso do mesmo token (item 45 —
    pensar cenário de abuso: token de reset não pode ser reaproveitado
    depois de já ter trocado a senha uma vez).
    """
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
