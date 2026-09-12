from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.exceptions import (
    AccountInactive,
    AccountLocked,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidResetToken,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserPublic,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    """
    Item 35 (cadastro). Decisão registrada em docs/decisions.md: v1
    não faz verificação de e-mail (conta ativa na hora) porque nenhum
    provedor de envio de e-mail está conectado ainda — isso é
    revisitado quando a ETAPA 22 (notificações) ligar o canal de
    e-mail de verdade.

    Rate limit por IP (ETAPA 35): 10/minuto — cadastro em massa
    automatizado é o abuso mais óbvio contra uma rota sem
    autenticação nenhuma.
    """
    try:
        user = auth_service.register_user(db, payload.email, payload.password)
    except EmailAlreadyRegistered:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="e-mail já cadastrado")
    return user


@router.post("/login", response_model=TokenPair)
@limiter.limit("10/minute")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Rate limit por IP (ETAPA 35): 10/minuto. Complementa, não
    substitui, o bloqueio por CONTA já existente
    (`failed_login_attempts`/`locked_until`, ETAPA 6) — aquele impede
    força bruta contra uma conta específica; este impede um único IP
    de testar senha contra MUITAS contas diferentes, o que o bloqueio
    por conta sozinho não pega.
    """
    try:
        user = auth_service.authenticate(
            db, payload.email, payload.password, ip_address=request.client.host if request.client else None
        )
    except AccountLocked as exc:
        raise HTTPException(status.HTTP_423_LOCKED, detail=str(exc))
    except AccountInactive:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="conta inativa")
    except InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="e-mail ou senha inválidos")

    access_token, refresh_token = auth_service.issue_tokens(
        db, user, user_agent=request.headers.get("user-agent"), ip_address=request.client.host if request.client else None
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit("30/minute")
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    try:
        access_token, refresh_token = auth_service.rotate_refresh_token(
            db,
            payload.refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except InvalidRefreshToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="refresh token inválido, expirado ou revogado")
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    auth_service.revoke_refresh_token(db, payload.refresh_token)


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        auth_service.change_password(db, current_user, payload.current_password, payload.new_password)
    except InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="senha atual incorreta")


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
def request_password_reset(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    """
    Sempre responde 202, exista ou não o e-mail — evita que alguém
    descubra quais e-mails têm conta testando este endpoint. O token
    gerado ainda não é entregue por e-mail (nenhum provedor conectado
    nesta etapa); ver nota em docs/decisions.md.

    Rate limit por IP (ETAPA 35): 5/minuto — gerar token de reset é
    mais caro (grava no banco) que uma checagem de senha, então o
    limite é mais apertado que o de login.
    """
    auth_service.create_password_reset_token(db, payload.email)
    return {"detail": "se o e-mail existir, instruções de recuperação serão enviadas"}


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
def confirm_password_reset(payload: PasswordResetConfirm, request: Request, db: Session = Depends(get_db)):
    try:
        auth_service.reset_password(db, payload.token, payload.new_password)
    except InvalidResetToken:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="token de recuperação inválido, expirado ou já usado")
