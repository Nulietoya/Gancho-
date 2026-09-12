import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_active_relationship, require_relationship_permission
from app.core.database import get_db
from app.core.exceptions import (
    InterventionNotFound,
    InvalidInterventionTransition,
    InvalidInviteToken,
    PersonalPlanNotFound,
    RelationshipNotFound,
)
from app.models.enums import PermissionKey, TaskOrigin
from app.models.trust import TrustedPersonRelationship
from app.models.user import User
from app.schemas.dashboard import TrustedDashboard
from app.schemas.intervention import InterventionPublic
from app.schemas.personal_plan import PersonalPlanPublic
from app.schemas.task import SuggestTaskRequest, TaskPublic
from app.schemas.trust import (
    AcceptInviteRequest,
    InviteRequest,
    ObservationCreate,
    ObservationPublic,
    PermissionsUpdateRequest,
    RelationshipAsTrustedPublic,
    RelationshipPublic,
)
from app.services import dashboard_service, intervention_service, personal_plan_service, task_service, trust_service

router = APIRouter(prefix="/trusted-people", tags=["trusted-people"])


@router.post("/invite", response_model=RelationshipPublic, status_code=status.HTTP_201_CREATED)
def invite(
    payload: InviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return trust_service.invite_trusted_person(db, current_user, payload.email, payload.relationship_label)


@router.post("/accept", response_model=RelationshipPublic)
def accept(
    payload: AcceptInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return trust_service.accept_invite(db, current_user, payload.invite_token)
    except InvalidInviteToken:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="convite inválido, já usado ou endereçado a outro e-mail")


@router.get("", response_model=list[RelationshipPublic])
def list_my_trusted_people(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return trust_service.list_relationships_for_owner(db, current_user)


@router.get("/watching", response_model=list[RelationshipAsTrustedPublic])
def list_accounts_i_watch(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    ETAPA 27 (6ª leva): ponto de entrada do painel operacional da
    pessoa de confiança — antes de abrir o dashboard de alguém
    específico, ela precisa de uma lista de quem está acompanhando (a
    mesma conta pode ser pessoa de confiança de várias pessoas ao
    mesmo tempo). Rota declarada antes de `/{relationship_id}/...`
    para não competir com o path dinâmico, embora "watching" nunca
    validaria como UUID mesmo se a ordem fosse invertida.
    """
    pairs = trust_service.list_relationships_for_trusted_person(db, current_user)
    return [
        RelationshipAsTrustedPublic(
            **RelationshipPublic.model_validate(relationship).model_dump(),
            owner_display_name=display_name,
        )
        for relationship, display_name in pairs
    ]


@router.put("/{relationship_id}/permissions", response_model=RelationshipPublic)
def update_permissions(
    relationship_id: uuid.UUID,
    payload: PermissionsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return trust_service.update_permissions(
            db,
            current_user,
            relationship_id,
            [(p.permission_key, p.is_granted, p.indicator_scope) for p in payload.permissions],
        )
    except RelationshipNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="relacionamento não encontrado")


@router.post("/{relationship_id}/revoke", response_model=RelationshipPublic)
def revoke(
    relationship_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return trust_service.revoke_relationship(db, current_user, relationship_id)
    except RelationshipNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="relacionamento não encontrado")


@router.post(
    "/{relationship_id}/observations",
    response_model=ObservationPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_observation(
    payload: ObservationCreate,
    current_user: User = Depends(get_current_user),
    relationship: TrustedPersonRelationship = Depends(
        require_relationship_permission(PermissionKey.RECORD_OBSERVATION)
    ),
    db: Session = Depends(get_db),
):
    """
    Chamado pela PESSOA DE CONFIANÇA, nunca pelo dono da conta —
    `relationship_id` identifica de quem ela tem permissão pra
    observar. A dependency `require_relationship_permission` já
    garante RECORD_OBSERVATION concedida antes de a função rodar;
    sem isso, a requisição nem chega aqui (403 antes).
    """
    return trust_service.record_observation(
        db,
        relationship=relationship,
        trusted_user=current_user,
        category=payload.category,
        since=payload.since,
        intensity=payload.intensity,
        note=payload.note,
    )


@router.post(
    "/{relationship_id}/tasks/suggest",
    response_model=TaskPublic,
    status_code=status.HTTP_201_CREATED,
)
def suggest_task(
    payload: SuggestTaskRequest,
    relationship: TrustedPersonRelationship = Depends(
        require_relationship_permission(PermissionKey.SUGGEST_TASK)
    ),
    db: Session = Depends(get_db),
):
    """
    Item 24 (nível de permissão 2 — "Apoiar: sugerir tarefa ou
    ação"). A tarefa nasce na conta do DONO (`relationship.owner_user_id`),
    não da pessoa de confiança — ela só aparece na lista de tarefas do
    dono, marcada com a origem e o relacionamento de onde veio, e o
    dono decide o que fazer com ela como qualquer outra tarefa seguindo.
    """
    return task_service.create_task(
        db,
        relationship.owner_user_id,
        payload.model_dump(),
        origin=TaskOrigin.TRUSTED_PERSON_SUGGESTION,
        source_relationship_id=relationship.id,
    )


@router.post(
    "/{relationship_id}/interventions/{intervention_id}/accept",
    response_model=InterventionPublic,
)
def accept_intervention(
    intervention_id: uuid.UUID,
    relationship: TrustedPersonRelationship = Depends(
        require_relationship_permission(PermissionKey.HELP_WITH_TASK)
    ),
    db: Session = Depends(get_db),
):
    """
    Item 24 — primeiro uso real de HELP_WITH_TASK (registrada como
    "sem uso por ora" na decisão da ETAPA 10): aceitar um pedido de
    body doubling que o dono endereçou especificamente a esta pessoa
    de confiança (`support_relationship_id`), nunca qualquer
    intervenção de qualquer pessoa com essa permissão concedida — ver
    docstring de `accept_intervention_by_trusted_person`.
    """
    try:
        return intervention_service.accept_intervention_by_trusted_person(db, relationship, intervention_id)
    except InterventionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="intervenção não encontrada")
    except InvalidInterventionTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{relationship_id}/dashboard", response_model=TrustedDashboard)
def get_trusted_dashboard(
    relationship: TrustedPersonRelationship = Depends(require_active_relationship),
    db: Session = Depends(get_db),
):
    """
    ETAPA 23/24 — visão da pessoa de confiança sobre o dono deste
    relacionamento. Nenhuma permissão única é exigida pra rota
    responder (`require_active_relationship` só garante que o
    relacionamento existe, pertence a quem está autenticado e está
    ativo) — cada seção do corpo da resposta aparece ou não conforme a
    permissão concedida, ver `dashboard_service.build_trusted_dashboard`.
    """
    return dashboard_service.build_trusted_dashboard(db, relationship)


@router.get("/{relationship_id}/personal-plan", response_model=PersonalPlanPublic)
def get_personal_plan(
    relationship: TrustedPersonRelationship = Depends(
        require_relationship_permission(PermissionKey.ACCESS_CRISIS_PLAN)
    ),
    db: Session = Depends(get_db),
):
    """
    Item 19/45 — nível de permissão 5 ("crise: acessar plano
    previamente autorizado"). Disponível pra pessoa de confiança a
    qualquer momento, não só durante um estado VERMELHO: o ponto de um
    plano estilo WRAP é a pessoa de apoio já conhecer o conteúdo ANTES
    de precisar dele.
    """
    try:
        return personal_plan_service.get_active_plan_for_relationship(db, relationship)
    except PersonalPlanNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="esta pessoa ainda não escreveu um plano")


@router.get("/{relationship_id}/observations", response_model=list[ObservationPublic])
def list_observations(
    relationship_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Só o dono da conta observada vê as observações registradas sobre ele."""
    try:
        return trust_service.list_observations_for_relationship(db, current_user, relationship_id)
    except RelationshipNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="relacionamento não encontrado")
