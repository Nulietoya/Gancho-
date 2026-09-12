"""
Testes do modelo de dados (ETAPA 4). Não testam regra de negócio
ainda (isso vem com os services, ETAPA 6+) — testam que o schema em
si impõe o que o documento de referência exige: relacionamento
único, permissão granular por linha, cascade correto ao remover um
usuário.
"""
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    DailyCheckIn,
    Permission,
    Profile,
    TrustedPersonRelationship,
    User,
)
from app.models.enums import PermissionKey, RelationshipStatus


def make_user(db_session, email="user@example.com") -> User:
    user = User(email=email, password_hash="hashed")
    db_session.add(user)
    db_session.flush()
    return user


def test_create_user_with_profile(db_session):
    user = make_user(db_session)
    profile = Profile(user_id=user.id, display_name="Nulie")
    db_session.add(profile)
    db_session.flush()

    assert profile.id is not None
    assert profile.tone_preference.value == "companheiro_calmo"  # default do documento


def test_checkin_is_unique_per_user_per_day(db_session):
    user = make_user(db_session)
    today = date.today()

    db_session.add(
        DailyCheckIn(user_id=user.id, checkin_date=today, mood=4, submitted_at=datetime.now(timezone.utc))
    )
    db_session.flush()

    db_session.add(
        DailyCheckIn(user_id=user.id, checkin_date=today, mood=2, submitted_at=datetime.now(timezone.utc))
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_checkin_allows_all_indicators_optional(db_session):
    """Item 6 do documento: check-in não pode obrigar todas as perguntas."""
    user = make_user(db_session)
    checkin = DailyCheckIn(
        user_id=user.id,
        checkin_date=date.today(),
        mood=3,
        submitted_at=datetime.now(timezone.utc),
        # energy, anxiety, ability_to_start_tasks etc. deliberadamente omitidos
    )
    db_session.add(checkin)
    db_session.flush()

    assert checkin.energy is None
    assert checkin.anxiety is None


def test_trusted_person_relationship_permissions_are_granular(db_session):
    """
    Item 45/70: uma pessoa de confiança autenticada pode ter uma
    permissão concedida e outra negada na mesma relação — não é
    tudo-ou-nada.
    """
    owner = make_user(db_session, "owner@example.com")

    relationship = TrustedPersonRelationship(
        owner_user_id=owner.id,
        invite_email="confianca@example.com",
        invite_token=str(uuid.uuid4()),
        status=RelationshipStatus.ACCEPTED,
        invited_at=datetime.now(timezone.utc),
        accepted_at=datetime.now(timezone.utc),
    )
    db_session.add(relationship)
    db_session.flush()

    db_session.add_all([
        Permission(
            relationship_id=relationship.id,
            permission_key=PermissionKey.RECORD_OBSERVATION,
            is_granted=True,
            granted_at=datetime.now(timezone.utc),
        ),
        Permission(
            relationship_id=relationship.id,
            permission_key=PermissionKey.VIEW_MEDICATION,
            is_granted=False,
        ),
    ])
    db_session.flush()

    granted = {
        p.permission_key: p.is_granted
        for p in db_session.query(Permission).filter_by(relationship_id=relationship.id)
    }
    assert granted[PermissionKey.RECORD_OBSERVATION] is True
    assert granted[PermissionKey.VIEW_MEDICATION] is False


def test_duplicate_permission_key_per_relationship_is_rejected(db_session):
    owner = make_user(db_session, "owner2@example.com")
    relationship = TrustedPersonRelationship(
        owner_user_id=owner.id,
        invite_email="confianca2@example.com",
        invite_token=str(uuid.uuid4()),
        status=RelationshipStatus.ACCEPTED,
        invited_at=datetime.now(timezone.utc),
    )
    db_session.add(relationship)
    db_session.flush()

    db_session.add(
        Permission(relationship_id=relationship.id, permission_key=PermissionKey.SUGGEST_TASK, is_granted=True)
    )
    db_session.flush()

    db_session.add(
        Permission(relationship_id=relationship.id, permission_key=PermissionKey.SUGGEST_TASK, is_granted=False)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_user_cascades_to_profile(db_session):
    user = make_user(db_session, "todelete@example.com")
    db_session.add(Profile(user_id=user.id, display_name="Temp"))
    db_session.flush()

    db_session.delete(user)
    db_session.flush()

    assert db_session.query(Profile).filter_by(user_id=user.id).first() is None
