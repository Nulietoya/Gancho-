"""
Regras de negócio da autenticação (ETAPA 6). Nada aqui sabe o que é
uma requisição HTTP — recebe uma Session do SQLAlchemy e valores já
validados pelo schema, devolve models ou levanta uma exceção de
app.core.exceptions. A tradução pra HTTP status code é feita só em
app/api/v1/auth.py.
"""
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import email
from app.core.config import get_settings
from app.core.exceptions import (
    AccountInactive,
    AccountLocked,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidResetToken,
    RefreshTokenReused,
)
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.core.time import utc_now
from app.models.audit import AuditLog
from app.models.auth import PasswordResetToken, RefreshSession
from app.models.enums import AuditAction
from app.models.user import User

settings = get_settings()

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
PASSWORD_RESET_TOKEN_MINUTES = 30


def register_user(db: Session, email: str, password: str) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegistered(email)

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str, ip_address: str | None = None) -> User:
    """
    Nunca revela, por diferença de resposta, se o e-mail existe ou
    não (item 30 — minimização, e proteção contra enumeração de
    usuários): credencial errada e e-mail inexistente levantam a
    mesma InvalidCredentials.

    Login bem-sucedido grava `AuditLog` (`AuditAction.LOGIN`, item 31
    — enum existia desde o início mas nunca era gravado, confirmado ao
    vivo via grep antes da ETAPA 26). Login FALHO não gera linha aqui
    de propósito: já tem seu próprio controle (`failed_login_attempts`/
    `locked_until`) e uma trilha de tentativas falhas por e-mail seria,
    ela mesma, um vetor de enumeração de conta se exposta na consulta
    de auditoria do item 31.
    """
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        # gasta um hash mesmo sem usuário, pra não vazar por tempo de resposta
        # se o e-mail existe ou não.
        hash_password(password)
        raise InvalidCredentials(email)

    now = utc_now()
    if user.locked_until is not None and user.locked_until > now:
        raise AccountLocked(user.locked_until)

    if not user.is_active or user.deactivated_at is not None:
        raise AccountInactive(email)

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
        db.commit()
        raise InvalidCredentials(email)

    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(
        AuditLog(
            actor_user_id=user.id,
            target_user_id=user.id,
            action=AuditAction.LOGIN,
            log_metadata={},
            ip_address=ip_address,
            created_at=now,
        )
    )
    db.commit()
    return user


def issue_tokens(
    db: Session, user: User, user_agent: str | None = None, ip_address: str | None = None
) -> tuple[str, str]:
    access_token = create_access_token(subject=str(user.id))

    refresh_raw = generate_opaque_token()
    now = utc_now()
    session = RefreshSession(
        user_id=user.id,
        token_hash=hash_opaque_token(refresh_raw),
        issued_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(session)
    db.commit()
    return access_token, refresh_raw


def _get_active_refresh_session(db: Session, raw_refresh_token: str) -> RefreshSession:
    """
    Busca a sessão correspondente a um refresh token, distinguindo dois
    casos que antes eram tratados como o mesmo erro genérico:

    - token não existe ou expirou: erro comum (nunca existiu, ou já
      passou do prazo) — InvalidRefreshToken de sempre.
    - token existe mas já está `revoked_at` (foi rotacionado numa
      troca anterior, ou revogado por logout/troca de senha/etc): o
      dono legítimo já não deveria mais ter esse valor em mãos, então
      alguém apresentando ele de novo é sinal de possível roubo de
      sessão (replay de um refresh token copiado antes da rotação).
      Reage revogando toda sessão ativa do usuário — o mesmo já feito
      em troca de senha — e registra em auditoria, antes de levantar
      RefreshTokenReused (que a rota trata como o mesmo 401 genérico,
      pra não confirmar a detecção pro possível atacante).
    """
    token_hash = hash_opaque_token(raw_refresh_token)
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash))
    now = utc_now()
    if session is None or session.expires_at < now:
        raise InvalidRefreshToken()
    if session.revoked_at is not None:
        user = db.get(User, session.user_id)
        if user is not None:
            revoke_all_sessions(db, user)
            db.add(
                AuditLog(
                    actor_user_id=user.id,
                    target_user_id=user.id,
                    action=AuditAction.SUSPECTED_SESSION_THEFT,
                    log_metadata={"via": "refresh_token_reuse"},
                    created_at=utc_now(),
                )
            )
            db.commit()
        raise RefreshTokenReused()
    return session


def rotate_refresh_token(
    db: Session, raw_refresh_token: str, user_agent: str | None = None, ip_address: str | None = None
) -> tuple[str, str]:
    """
    Rotação: todo uso de um refresh token o invalida e emite um novo.
    Isso limita o estrago de um token roubado a uma única troca — se o
    token antigo for reapresentado depois (pelo dono legítimo tentando
    usar uma cópia obsoleta, ou por um invasor que copiou o token antes
    da rotação), `_get_active_refresh_session` detecta o reuso e revoga
    toda sessão do usuário, forçando login de novo em todo dispositivo.
    """
    session = _get_active_refresh_session(db, raw_refresh_token)
    user = db.get(User, session.user_id)
    if user is None or not user.is_active or user.deactivated_at is not None:
        raise InvalidRefreshToken()

    session.revoked_at = utc_now()
    db.commit()

    return issue_tokens(db, user, user_agent=user_agent, ip_address=ip_address)


def revoke_refresh_token(db: Session, raw_refresh_token: str) -> None:
    token_hash = hash_opaque_token(raw_refresh_token)
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash))
    if session is not None and session.revoked_at is None:
        session.revoked_at = utc_now()
        db.commit()


def revoke_all_sessions(db: Session, user: User) -> None:
    now = utc_now()
    db.query(RefreshSession).filter(
        RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None)
    ).update({"revoked_at": now})
    db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise InvalidCredentials(user.email)

    user.password_hash = hash_password(new_password)
    db.add(
        AuditLog(
            actor_user_id=user.id,
            target_user_id=user.id,
            action=AuditAction.PASSWORD_CHANGE,
            log_metadata={"via": "change_password"},
            created_at=utc_now(),
        )
    )
    db.commit()
    # Trocar a senha invalida toda sessão existente — inclusive a de
    # um invasor que tenha obtido acesso antes da troca.
    revoke_all_sessions(db, user)


def create_password_reset_token(db: Session, email_address: str) -> str | None:
    """
    Devolve o token em claro pra quem chamou (usado pelos testes, que
    não têm como ler uma caixa de e-mail de verdade) — o canal real
    de entrega é o e-mail disparado aqui dentro (ETAPA 22: antes disso
    o token só existia no banco, sem nenhum jeito de a pessoa recebê-lo
    fora de um teste). Devolve None se o e-mail não existe; a rota
    HTTP responde a mesma coisa nos dois casos pra não vazar quais
    e-mails têm conta (proteção contra enumeração, mesmo raciocínio
    do login).
    """
    user = db.scalar(select(User).where(User.email == email_address))
    if user is None:
        return None

    raw_token = generate_opaque_token()
    now = utc_now()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            created_at=now,
            expires_at=now + timedelta(minutes=PASSWORD_RESET_TOKEN_MINUTES),
        )
    )
    db.commit()

    reset_link = f"{settings.frontend_url}/reset-password?token={raw_token}"
    email.send_email(
        email_address,
        "Gancho — redefinir sua senha",
        f"Alguém (esperamos que você) pediu pra redefinir a senha da sua conta Gancho.\n\n"
        f"Link: {reset_link}\n\n"
        f"Se não foi você, ignore este e-mail — sua senha continua a mesma. "
        f"O link expira em {PASSWORD_RESET_TOKEN_MINUTES} minutos.",
    )
    return raw_token


def reset_password(db: Session, raw_token: str, new_password: str) -> None:
    token_hash = hash_opaque_token(raw_token)
    reset_token = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    now = utc_now()

    if (
        reset_token is None
        or reset_token.used_at is not None
        or reset_token.expires_at < now
    ):
        raise InvalidResetToken()

    user = db.get(User, reset_token.user_id)
    if user is None:
        raise InvalidResetToken()

    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    reset_token.used_at = now
    db.add(
        AuditLog(
            actor_user_id=user.id,
            target_user_id=user.id,
            action=AuditAction.PASSWORD_CHANGE,
            log_metadata={"via": "reset_password"},
            created_at=now,
        )
    )
    db.commit()
    revoke_all_sessions(db, user)
