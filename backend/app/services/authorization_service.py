"""
ETAPA 7 — Autorização: "o que pode fazer", separado de autenticação
("quem é", ETAPA 6). Este módulo é o único lugar do backend que
decide se uma pessoa de confiança pode agir sobre a conta de outra
pessoa — nenhuma rota confere permissão sozinha, todas chamam
`require_relationship_permission`.

Nada aqui é cacheado: cada chamada relê o estado atual do
relacionamento e da permissão no banco. Isso é deliberado — é o que
garante que uma revogação feita agora vale imediatamente na próxima
requisição, sem depender de um token carregar a permissão consigo
(item 71: revogação não pode ser contornada por algo emitido antes).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import PermissionDenied, RelationshipNotFound
from app.core.time import utc_now
from app.models.audit import AuditLog
from app.models.enums import AuditAction, PermissionKey, RelationshipStatus
from app.models.trust import Permission, TrustedPersonRelationship


def require_relationship_permission(
    db: Session,
    *,
    relationship_id: uuid.UUID,
    trusted_user_id: uuid.UUID,
    permission_key: PermissionKey,
) -> TrustedPersonRelationship:
    """
    Levanta RelationshipNotFound se o relacionamento não existe ou não
    pertence a `trusted_user_id` (nunca revela se existe para outra
    pessoa — mesmo princípio anti-enumeração da autenticação).
    Levanta PermissionDenied — e registra a tentativa em AuditLog —
    se o relacionamento não estiver ativo ou a permissão específica
    não estiver concedida.
    """
    relationship = db.scalar(
        select(TrustedPersonRelationship).where(
            TrustedPersonRelationship.id == relationship_id,
            TrustedPersonRelationship.trusted_user_id == trusted_user_id,
        )
    )
    if relationship is None:
        raise RelationshipNotFound(relationship_id)

    if relationship.status != RelationshipStatus.ACCEPTED or relationship.revoked_at is not None:
        _log_denied_access(db, relationship, trusted_user_id, permission_key)
        raise PermissionDenied(permission_key)

    permission = db.scalar(
        select(Permission).where(
            Permission.relationship_id == relationship.id,
            Permission.permission_key == permission_key,
        )
    )
    if permission is None or not permission.is_granted:
        _log_denied_access(db, relationship, trusted_user_id, permission_key)
        raise PermissionDenied(permission_key)

    return relationship


def get_active_relationship_for_trusted_user(
    db: Session, *, relationship_id: uuid.UUID, trusted_user_id: uuid.UUID
) -> TrustedPersonRelationship:
    """
    ETAPA 23/24 — usado pelo dashboard da pessoa de confiança, onde
    nenhuma permissão única é obrigatória pra rota responder: cada
    seção do corpo da resposta decide por conta própria, olhando pra
    este mesmo relacionamento, se tem permissão pra aparecer (ver
    `dashboard_service.build_trusted_dashboard`). Ainda assim exige
    relacionamento existente, pertencente a este usuário como pessoa
    de confiança, e ativo (aceito e não revogado) — sem isso, nem
    chega a decidir seção nenhuma. Mesmo "404 não 403" do resto da
    camada de autorização: relacionamento inativo devolve o mesmo erro
    de relacionamento inexistente, nunca revela que existe mas está
    revogado.
    """
    relationship = db.scalar(
        select(TrustedPersonRelationship)
        .options(selectinload(TrustedPersonRelationship.permissions))
        .where(
            TrustedPersonRelationship.id == relationship_id,
            TrustedPersonRelationship.trusted_user_id == trusted_user_id,
        )
    )
    if relationship is None:
        raise RelationshipNotFound(relationship_id)
    if relationship.status != RelationshipStatus.ACCEPTED or relationship.revoked_at is not None:
        raise RelationshipNotFound(relationship_id)
    return relationship


def _log_denied_access(
    db: Session,
    relationship: TrustedPersonRelationship,
    actor_user_id: uuid.UUID,
    permission_key: PermissionKey,
) -> None:
    """
    Item 31/54: registra a tentativa negada sem nunca gravar o dado em
    si — só qual permissão foi negada e para o relacionamento de quem.
    """
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            target_user_id=relationship.owner_user_id,
            action=AuditAction.RESTRICTED_DATA_ACCESS_DENIED,
            log_metadata={"relationship_id": str(relationship.id), "permission_key": permission_key.value},
            created_at=utc_now(),
        )
    )
    db.commit()
