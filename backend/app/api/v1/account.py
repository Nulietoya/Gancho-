"""ETAPA 25 (item 53) — rotas de ciclo de vida de conta (LGPD: exportação e exclusão)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import InvalidAccountPassword
from app.models.user import User
from app.schemas.account import AccountDeleteRequest
from app.services import account_service

router = APIRouter(prefix="/account", tags=["account"])


@router.post("/delete", status_code=status.HTTP_200_OK)
def delete_account(
    payload: AccountDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Item 53 — exclusão definitiva (decisão revertida em 2026-09-22, ver
    docstring de `account_service.delete_account`: era soft delete,
    agora apaga de verdade). Reconfirma senha antes de agir, mesmo
    critério de `auth_service.change_password`. Sem idempotência aqui
    por definição: a segunda chamada não tem mais conta nem token pra
    chegar até aqui — `get_current_user` já rejeita antes.
    """
    try:
        account_service.delete_account(db, current_user, payload.password)
    except InvalidAccountPassword:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="senha incorreta")
    return {"deleted": True}


@router.get("/export")
def export_account_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Item 53 — portabilidade. Retorna um retrato JSON dos dados da própria conta."""
    return account_service.export_account_data(db, current_user)
