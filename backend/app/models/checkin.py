import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin


class DailyCheckIn(IdMixin, TimestampMixin, Base):
    """
    Item 6 — extremamente curto por design. Todo indicador é
    opcional (a pessoa piorando tem menos disposição pra preencher
    formulário longo); a validação de "pelo menos um campo
    preenchido" fica no schema/serviço, não é uma constraint de banco
    que impediria salvar um check-in parcial.

    `extra_answers` guarda respostas de perguntas expandidas
    (opcionais, não diárias) sem exigir migration por pergunta nova.
    """
    __tablename__ = "daily_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_checkin_user_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    anxiety: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    ability_to_start_tasks: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    willingness_to_interact: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    sense_of_functioning: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5

    extra_answers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
