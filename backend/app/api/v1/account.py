"""ETAPA 25 (item 53) — rotas de ciclo de vida de conta (LGPD: exportação e exclusão)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import InvalidAccountPassword
from app.models.user import User
from app.schemas.account import AccountDeactivateRequest
from app.services import account_service

router = APIRouter(prefix="/account", tags=["account"])


@router.post("/deactivate", status_code=status.HTTP_200_OK)
def deactivate_account(
    payload: AccountDeactivateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Item 53 — exclusão (soft delete). Reconfirma senha antes de agir,
    mesmo critério de `auth_service.change_password`. Idempotente: uma
    segunda chamada não levanta erro, só devolve o estado já desativado
    (embora, na prática, a sessão já tenha sido revogada na primeira
    chamada — a pessoa precisaria de outra sessão viva, o que não deveria
    acontecer já que `revoke_all_sessions` derruba todas).
    """
    try:
        user = account_service.deactivate_account(db, current_user, payload.password)
    except InvalidAccountPassword:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="senha incorreta")
    return {"deactivated": True, "deactivated_at": user.deactivated_at.isoformat()}


@router.get("/export")
def export_account_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Item 53 — portabilidade. Retorna um retrato JSON dos dados da própria conta."""
    return account_service.export_account_data(db, current_user)
