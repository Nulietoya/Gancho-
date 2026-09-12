import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import PermissionKey, RelationshipStatus


class TrustedPersonRelationship(IdMixin, TimestampMixin, Base):
    """
    Item 14. `trusted_user_id` fica nulo até a pessoa convidada criar
    a própria conta e aceitar — o convite existe antes da conta
    existir. Revogação nunca apaga a linha (precisa sobreviver para
    auditoria e para o cenário de teste do item 71); em vez disso
    marca `revoked_at` e todo token/sessão ligado a ela para de
    autorizar a partir daquele instante (verificado no middleware de
    autorização, não confiar em cache).
    """
    __tablename__ = "trusted_person_relationships"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "trusted_user_id", name="uq_relationship_owner_trusted"),
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trusted_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    invite_email: Mapped[str] = mapped_column(String(320), nullable=False)
    invite_token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    relationship_label: Mapped[str | None] = mapped_column(String(80), nullable=True)

    status: Mapped[RelationshipStatus] = mapped_column(default=RelationshipStatus.PENDING, nullable=False)
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    permissions: Mapped[list["Permission"]] = relationship(
        back_populates="relationship_", cascade="all, delete-orphan"
    )


class Permission(IdMixin, TimestampMixin, Base):
    """
    Uma linha por (relacionamento, tipo de permissão) em vez de
    colunas fixas booleanas — permite testar cada permissão de forma
    isolada (item 45/70: "pessoa de confiança autenticada, ainda
    assim não pode visualizar X sem permissão explícita") e adicionar
    novas permissões sem migration estrutural.

    `indicator_scope` só é usado quando permission_key =
    VIEW_SPECIFIC_INDICATORS: lista de IndicatorKey liberados.
    """
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("relationship_id", "permission_key", name="uq_permission_relationship_key"),
    )

    relationship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trusted_person_relationships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_key: Mapped[PermissionKey] = mapped_column(nullable=False)
    is_granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    indicator_scope: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    relationship_: Mapped[TrustedPersonRelationship] = relationship(back_populates="permissions")
