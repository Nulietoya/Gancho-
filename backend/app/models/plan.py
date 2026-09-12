import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import PersonalPlanSignal


class PersonalPlan(IdMixin, TimestampMixin, Base):
    """
    Item 19 — "Plano quando eu não perceber", estilo WRAP: escrito
    pelo próprio usuário durante período estável, não pelo sistema.
    """
    __tablename__ = "personal_plans"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    rules: Mapped[list["PersonalPlanRule"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class PersonalPlanRule(IdMixin, TimestampMixin, Base):
    """Item 19 — sinal configurável ('faltas', 'isolamento', 'sono', ...) com limiar em texto do próprio usuário."""
    __tablename__ = "personal_plan_rules"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personal_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    signal_key: Mapped[PersonalPlanSignal] = mapped_column(nullable=False)
    threshold_description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    plan: Mapped[PersonalPlan] = relationship(back_populates="rules")
