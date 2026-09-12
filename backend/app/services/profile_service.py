"""
Regras de negócio de perfil/onboarding (ETAPA 8/9). Mesma separação
das demais services: nada aqui sabe o que é uma requisição HTTP.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ProfileAlreadyExists, ProfileNotFound
from app.core.time import utc_now
from app.models.user import Profile, User


def get_profile(db: Session, user: User) -> Profile:
    if user.profile is None:
        raise ProfileNotFound(str(user.id))
    return user.profile


def create_profile(db: Session, user: User, data: dict) -> Profile:
    if user.profile is not None:
        raise ProfileAlreadyExists(str(user.id))

    profile = Profile(user_id=user.id, **data)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(db: Session, user: User, changes: dict) -> Profile:
    """
    `changes` já vem filtrado (via `model_dump(exclude_unset=True)`
    na rota) para conter só os campos que a pessoa de fato enviou —
    assim um PATCH com um único campo nunca apaga os outros.
    """
    profile = get_profile(db, user)
    for field, value in changes.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


def complete_onboarding(db: Session, user: User) -> Profile:
    """
    Marca o onboarding como concluído. Idempotente de propósito: from
    the app's point of view "completar de novo" não é um erro, é só
    confirmar de novo — não há necessidade de forçar todo campo de
    texto livre a estar preenchido (algumas respostas são
    legitimamente vazias), então a única validação real é "o perfil
    existe".
    """
    profile = get_profile(db, user)
    if profile.onboarding_completed_at is None:
        profile.onboarding_completed_at = utc_now()
        db.commit()
        db.refresh(profile)
    return profile
