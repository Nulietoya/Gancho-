import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import ToneStyle


class User(IdMixin, TimestampMixin, Base):
    """
    Conta e credenciais. Não guarda nenhum dado comportamental —
    isso é responsabilidade de Profile e das tabelas de domínio.
    Isolar credenciais do resto facilita minimização de dados e
    exportação/exclusão (item 30/52/53).

    `failed_login_attempts`/`locked_until` implementam a "proteção
    contra abuso" do item 35 sem precisar de infraestrutura extra
    (Redis, rate limiter externo) — suficiente pro volume esperado no
    MVP; um rate limit por IP na borda (proxy/load balancer) é a
    camada que falta quando isso deixar de ser verdade.
    """
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Soft delete: uma conta excluída não é apagada na hora (retenção
    # legal + reversibilidade de erro), mas para de ser utilizável e
    # some das listagens. Apagamento físico é um job separado após o
    # prazo de retenção (item 53).
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Profile(IdMixin, TimestampMixin, Base):
    """
    Dados de onboarding (item 4) — contexto individual construído na
    primeira sessão de uso e revisável depois.
    """
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo", nullable=False)
    tone_preference: Mapped[ToneStyle] = mapped_column(
        default=ToneStyle.COMPANHEIRO_CALMO, nullable=False
    )

    main_responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_or_study: Mapped[str | None] = mapped_column(Text, nullable=True)
    habits: Mapped[str | None] = mapped_column(Text, nullable=True)
    patterns_considered_normal: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurring_difficulties: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Item: "sinais que costuma apresentar quando começa a funcionar
    # pior" — autorreconhecidos, texto livre, plural.
    self_recognized_warning_signs: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    privacy_preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")
