"""
ETAPA 14 (pessoas de confiança) construída junto com a ETAPA 7
(autorização) e a ETAPA 16 (observações externas) — decisão registrada
em docs/decisions.md: autorização sem um recurso concreto pra proteger
é abstração sem teste real, e observação externa é o próprio cenário
de autorização que o documento de referência usa como exemplo (itens
45/70). Construir os três juntos evita um módulo intermediário que
não faz nada sozinho.

Simplificação deliberada de escopo (também registrada em
decisions.md): convite não expira em v1 — pode ser revogado manualmente
pelo dono enquanto pendente. Adicionar expiração automática é uma
migration pequena quando isso importar de verdade.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core import email
from app.core.config import get_settings
from app.core.exceptions import InvalidInviteToken, RelationshipNotFound
from app.core.time import utc_now
from app.core.security import generate_opaque_token
from app.models.audit import AuditLog
from app.models.enums import AuditAction, ObservationCategory, ObservationIntensity, ObservationSince, PermissionKey, RelationshipStatus
from app.models.observation import Observation
from app.models.trust import Permission, TrustedPersonRelationship
from app.models.user import Profile, User


def invite_trusted_person(
    db: Session, owner: User, invite_email: str, relationship_label: str | None
) -> TrustedPersonRelationship:
    """
    Bug real corrigido: até esta revisão, o convite gerava e gravava
    `invite_token` no banco, mas nunca saía dali — `AuditAction.
    INVITE_SENT` era gravado no log de auditoria mesmo sem nenhum
    e-mail de fato ter sido enviado. Agora manda de verdade (mesmo
    caminho de `send_email` do reset de senha — nunca lança, só loga
    se falhar, então um provedor fora do ar não impede o convite de
    ser criado). O código também continua disponível na resposta da
    API (`InviteCreatedResponse`), pra quem convidou copiar e mandar
    na mão se o e-mail não chegar.
    """
    now = utc_now()
    relationship = TrustedPersonRelationship(
        owner_user_id=owner.id,
        invite_email=invite_email,
        invite_token=generate_opaque_token(),
        relationship_label=relationship_label,
        status=RelationshipStatus.PENDING,
        invited_at=now,
    )
    db.add(relationship)
    db.commit()
    db.refresh(relationship)

    db.add(
        AuditLog(
            actor_user_id=owner.id,
            target_user_id=owner.id,
            action=AuditAction.INVITE_SENT,
            log_metadata={"relationship_id": str(relationship.id)},
            created_at=now,
        )
    )
    db.commit()

    settings = get_settings()
    accept_link = f"{settings.frontend_url}/aceitar-convite?token={relationship.invite_token}"
    email.send_email(
        invite_email,
        "Gancho — convite para rede de confiança",
        f"{owner.email} convidou você para ser pessoa de confiança dela(e) no Gancho.\n\n"
        f"Pra aceitar, abra o link abaixo:\n{accept_link}\n\n"
        f"Se o link não abrir, entre no Gancho e cole este código na tela de aceitar convite:\n"
        f"{relationship.invite_token}\n\n"
        f"Você só vai poder ver o que essa pessoa autorizar depois, permissão por permissão — "
        f"aceitar o convite não dá acesso a nada por si só.\n\n"
        f"Se você não esperava este convite, pode ignorar este e-mail.",
    )
    return relationship


def accept_invite(db: Session, invitee: User, raw_invite_token: str) -> TrustedPersonRelationship:
    """
    Item 45: o convite é endereçado a um e-mail específico — aceitar
    logado com uma conta de e-mail diferente do convite é rejeitado,
    mesmo com o token certo (o token sozinho não é suficiente).
    """
    relationship = db.scalar(
        select(TrustedPersonRelationship).where(TrustedPersonRelationship.invite_token == raw_invite_token)
    )
    if relationship is None or relationship.status != RelationshipStatus.PENDING:
        raise InvalidInviteToken()
    if relationship.invite_email.lower() != invitee.email.lower():
        raise InvalidInviteToken()

    relationship.trusted_user_id = invitee.id
    relationship.status = RelationshipStatus.ACCEPTED
    relationship.accepted_at = utc_now()
    db.commit()
    db.refresh(relationship)
    return relationship


def list_relationships_for_owner(db: Session, owner: User) -> list[TrustedPersonRelationship]:
    return list(
        db.scalars(
            select(TrustedPersonRelationship)
            .where(TrustedPersonRelationship.owner_user_id == owner.id)
            .options(selectinload(TrustedPersonRelationship.permissions))
        )
    )


def list_relationships_for_trusted_person(db: Session, trusted_user: User) -> list[tuple[TrustedPersonRelationship, str]]:
    """
    Visão inversa de `list_relationships_for_owner` (ETAPA 27, 6ª
    leva): as contas que ESTE usuário acompanha como pessoa de
    confiança, nunca as que ele próprio convidou. Só relacionamentos
    ACEITOS aparecem — um convite ainda pendente não deu a esta pessoa
    nenhum acesso de verdade, e um revogado não deveria continuar
    aparecendo como se ainda desse acesso.

    Retorna pares (relacionamento, nome de exibição do dono) em vez de
    só o relacionamento porque `TrustedPersonRelationship` não guarda
    identidade nenhuma do dono pronta pra exibir — `invite_email` é o
    e-mail de quem foi CONVIDADO (a própria pessoa de confiança), não o
    do dono, então não serve de fallback aqui. Resolver o nome com duas
    queries em lote (nunca N+1) evita reabrir essa decisão em toda rota
    que precisar dela.
    """
    relationships = list(
        db.scalars(
            select(TrustedPersonRelationship)
            .where(
                TrustedPersonRelationship.trusted_user_id == trusted_user.id,
                TrustedPersonRelationship.status == RelationshipStatus.ACCEPTED,
            )
            .options(selectinload(TrustedPersonRelationship.permissions))
        )
    )
    owner_ids = [r.owner_user_id for r in relationships]
    display_names: dict[uuid.UUID, str] = {}
    owner_emails: dict[uuid.UUID, str] = {}
    if owner_ids:
        profiles = db.scalars(select(Profile).where(Profile.user_id.in_(owner_ids)))
        display_names = {p.user_id: p.display_name for p in profiles}
        owners = db.scalars(select(User).where(User.id.in_(owner_ids)))
        owner_emails = {u.id: u.email for u in owners}
    return [
        (r, display_names.get(r.owner_user_id) or owner_emails.get(r.owner_user_id, r.invite_email))
        for r in relationships
    ]


def get_relationship_for_owner(db: Session, owner: User, relationship_id: uuid.UUID) -> TrustedPersonRelationship:
    relationship = db.scalar(
        select(TrustedPersonRelationship)
        .where(TrustedPersonRelationship.id == relationship_id, TrustedPersonRelationship.owner_user_id == owner.id)
        .options(selectinload(TrustedPersonRelationship.permissions))
    )
    if relationship is None:
        raise RelationshipNotFound(relationship_id)
    return relationship


def update_permissions(
    db: Session, owner: User, relationship_id: uuid.UUID, updates: list[tuple[PermissionKey, bool, list[str] | None]]
) -> TrustedPersonRelationship:
    """
    `updates` é uma lista de (permission_key, is_granted, indicator_scope).
    Cada mudança de valor gera uma linha de AuditLog (item 31) — nunca
    resume "permissões atualizadas" num log só, porque o que importa
    auditar é exatamente qual permissão mudou e para qual estado.
    """
    relationship = get_relationship_for_owner(db, owner, relationship_id)
    now = utc_now()

    existing = {p.permission_key: p for p in relationship.permissions}

    for permission_key, is_granted, indicator_scope in updates:
        row = existing.get(permission_key)
        if row is None:
            row = Permission(relationship_id=relationship.id, permission_key=permission_key, is_granted=False)
            db.add(row)
            existing[permission_key] = row

        changed = row.is_granted != is_granted
        row.is_granted = is_granted
        row.indicator_scope = indicator_scope
        if changed and is_granted:
            row.granted_at = now
        if changed and not is_granted:
            row.revoked_at = now

        if changed:
            db.add(
                AuditLog(
                    actor_user_id=owner.id,
                    target_user_id=owner.id,
                    action=AuditAction.PERMISSION_GRANTED if is_granted else AuditAction.PERMISSION_REVOKED,
                    log_metadata={"relationship_id": str(relationship.id), "permission_key": permission_key.value},
                    created_at=now,
                )
            )

    db.commit()
    db.refresh(relationship)
    return relationship


def revoke_relationship(db: Session, owner: User, relationship_id: uuid.UUID) -> TrustedPersonRelationship:
    """
    Revoga o relacionamento inteiro: marca `revoked_at` (checado ao
    vivo em toda chamada de `require_relationship_permission`, então
    o efeito é imediato) e desliga toda permissão que estivesse
    concedida, uma AuditLog por permissão desligada.
    """
    relationship = get_relationship_for_owner(db, owner, relationship_id)
    now = utc_now()

    granted_keys = [p.permission_key for p in relationship.permissions if p.is_granted]
    if granted_keys:
        update_permissions(db, owner, relationship_id, [(key, False, None) for key in granted_keys])

    relationship.status = RelationshipStatus.REVOKED
    relationship.revoked_at = now
    db.commit()
    db.refresh(relationship)
    return relationship


def record_observation(
    db: Session,
    *,
    relationship: TrustedPersonRelationship,
    trusted_user: User,
    category: ObservationCategory,
    since: ObservationSince,
    intensity: ObservationIntensity,
    note: str | None,
) -> Observation:
    """
    `relationship` chega aqui já autorizado — a rota obtém esse valor
    através da dependency que chama
    `require_relationship_permission(..., PermissionKey.RECORD_OBSERVATION)`.
    Este service não reverifica a permissão: existe uma única fonte de
    verdade para "o que pode fazer" (item 36), e é ela.
    """
    now = utc_now()
    observation = Observation(
        owner_user_id=relationship.owner_user_id,
        relationship_id=relationship.id,
        category=category,
        since=since,
        intensity=intensity,
        note=note,
        recorded_at=now,
    )
    db.add(observation)
    db.add(
        AuditLog(
            actor_user_id=trusted_user.id,
            target_user_id=relationship.owner_user_id,
            action=AuditAction.EXTERNAL_OBSERVATION_RECORDED,
            log_metadata={"relationship_id": str(relationship.id), "category": category.value},
            created_at=now,
        )
    )
    db.commit()
    db.refresh(observation)
    return observation


def list_observations_for_relationship(
    db: Session, owner: User, relationship_id: uuid.UUID
) -> list[Observation]:
    get_relationship_for_owner(db, owner, relationship_id)  # 404 se não for o dono
    return list(
        db.scalars(
            select(Observation)
            .where(Observation.relationship_id == relationship_id)
            .order_by(Observation.recorded_at.desc())
        )
    )
