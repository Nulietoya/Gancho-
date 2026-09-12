"""
Regras de negócio de check-in diário (ETAPA 11, item 6). Um check-in
por usuário/dia (`UniqueConstraint` no model já garante isso no
banco); a data "hoje" é resolvida no fuso horário do perfil quando ele
existe (perfil ainda pode não existir se a pessoa não terminou o
onboarding — nesse caso cai pra UTC, mesma decisão simples adotada em
`Profile.timezone`, que também usa "America/Sao_Paulo" como default).
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import CheckInAlreadyExists, CheckInNotFound
from app.core.time import utc_now
from app.models.checkin import DailyCheckIn
from app.models.user import User
from app.services import indicator_service


def _today_for_user(user: User) -> date:
    tz_name = user.profile.timezone if user.profile else "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    return datetime.now(tz).date()


def create_checkin(db: Session, user: User, data: dict) -> DailyCheckIn:
    checkin_date = data.pop("checkin_date", None) or _today_for_user(user)

    existing = db.scalar(
        select(DailyCheckIn).where(DailyCheckIn.user_id == user.id, DailyCheckIn.checkin_date == checkin_date)
    )
    if existing is not None:
        raise CheckInAlreadyExists(str(checkin_date))

    checkin = DailyCheckIn(
        user_id=user.id,
        checkin_date=checkin_date,
        submitted_at=utc_now(),
        **data,
    )
    db.add(checkin)
    db.flush()
    indicator_service.sync_checkin_indicators(db, checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


def get_checkin(db: Session, user: User, checkin_date: date) -> DailyCheckIn:
    checkin = db.scalar(
        select(DailyCheckIn).where(DailyCheckIn.user_id == user.id, DailyCheckIn.checkin_date == checkin_date)
    )
    if checkin is None:
        raise CheckInNotFound(str(checkin_date))
    return checkin


def update_checkin(db: Session, user: User, checkin_date: date, changes: dict) -> DailyCheckIn:
    checkin = get_checkin(db, user, checkin_date)
    for field, value in changes.items():
        setattr(checkin, field, value)
    db.flush()
    indicator_service.sync_checkin_indicators(db, checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


def list_checkins(
    db: Session,
    user: User,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 30,
) -> list[DailyCheckIn]:
    stmt = select(DailyCheckIn).where(DailyCheckIn.user_id == user.id)
    if date_from is not None:
        stmt = stmt.where(DailyCheckIn.checkin_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(DailyCheckIn.checkin_date <= date_to)
    stmt = stmt.order_by(DailyCheckIn.checkin_date.desc()).limit(limit)
    return list(db.scalars(stmt))
