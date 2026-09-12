import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import ObservationCategory, ObservationIntensity, ObservationSince


class Observation(IdMixin, TimestampMixin, Base):
    """
    Item 15. Registrada por uma pessoa de confiança sobre o
    `owner_user_id` — a permissão RECORD_OBSERVATION do relacionamento
    correspondente é checada no service antes de criar a linha, nunca
    só no frontend (item 30/45).
    """
    __tablename__ = "observations"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trusted_person_relationships.id", ondelete="CASCADE"), nullable=False,
        index=True,  # ETAPA 30-32: trust_service.list_observations filtra por esta coluna direto
    )

    category: Mapped[ObservationCategory] = mapped_column(nullable=False)
    since: Mapped[ObservationSince] = mapped_column(nullable=False)
    intensity: Mapped[ObservationIntensity] = mapped_column(nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)  # pequena, descrição factual (item 15)

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
