"""
ETAPA 26 (item 31) — consolidação e consulta da trilha de auditoria.

Linhas de `AuditLog` já são gravadas por outros serviços desde a
ETAPA 7 (autorização, pessoas de confiança, observações externas) e
foram somando mais pontos de disparo a cada ETAPA (plano pessoal,
exportação/exclusão de conta). O trabalho real desta etapa foi achar
e fechar as lacunas: `AuditAction.LOGIN`, `PASSWORD_CHANGE` e
`CRITICAL_ALERT` existiam no enum desde o começo mas nunca eram
gravadas em lugar nenhum (confirmado ao vivo via grep antes de
começar) — mesmo padrão recorrente do projeto de peça "pré-modelada"
que só ganha comportamento quando a etapa certa chega. Essa parte foi
feita direto em `auth_service.py`/`alert_service.py`, não aqui.

Este módulo é só a metade "consulta": expõe pro próprio usuário o que
aconteceu com a conta dele, paginado (item 65 — nunca histórico
ilimitado de uma vez).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def list_audit_log(db: Session, user: User, limit: int = DEFAULT_LIMIT, offset: int = 0) -> list[dict]:
    """
    Só o que aconteceu À PRÓPRIA conta (`target_user_id`) — nunca o
    que o usuário fez como pessoa de confiança de outra conta (isso
    pertence ao audit log da outra pessoa, não ao dele). Mais recente
    primeiro.
    """
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.target_user_id == user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        {
            "id": row.id,
            "action": row.action,
            "actor_is_self": row.actor_user_id == user.id,
            "metadata": row.log_metadata,
            "created_at": row.created_at,
        }
        for row in rows
    ]
