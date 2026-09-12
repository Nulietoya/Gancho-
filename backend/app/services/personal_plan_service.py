"""
Plano pessoal (ETAPA 25, item 19 — "plano quando eu não perceber",
estilo WRAP). Model já existia desde a ETAPA 4, sem nenhuma lógica em
cima (conferido ao vivo contra o Postgres) — mesmo padrão de
`Notification`/`PersonalPlan` chegando "pré-modelado" e só ganhando
comportamento na etapa que o documento de referência de fato pede.

**Decisão de escopo registrada**: um usuário tem no máximo UM plano
ativo por vez — `create_plan` recusa (`PersonalPlanAlreadyExists`) se
já existir um. Isso é deliberado: o documento descreve o plano como
"o que fazer quando eu não perceber", um documento vivo que a pessoa
edita (`PATCH`), não uma sequência de versões históricas como
`Baseline`/`Routine` (que têm motivo real pra guardar versão anterior
— reclassificar o passado). Se a pessoa quiser recomeçar do zero,
desativa o atual (`deactivate_plan`, idempotente) e cria outro — sem
endpoint de reativação, de propósito: reativar um plano antigo sem
revisá-lo contraria o espírito de "escrito enquanto estável" (a pessoa
deveria reler e reescrever, não só destravar o texto de antes).

Toda mudança real (criar, editar, desativar plano; criar/editar regra)
gera uma linha em `AuditLog` com `AuditAction.PLAN_CHANGED` (item 31)
— um histórico de auditoria de quando o plano mudou é, em si, uma
informação relevante (a mesma ideia de confiabilidade histórica já
usada com observadores desde a proposta original do documento).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import PersonalPlanAlreadyExists, PersonalPlanNotFound, PersonalPlanRuleNotFound
from app.core.time import utc_now
from app.models.audit import AuditLog
from app.models.enums import AuditAction, PersonalPlanSignal
from app.models.plan import PersonalPlan, PersonalPlanRule
from app.models.trust import TrustedPersonRelationship
from app.models.user import User


def _log(db: Session, user_id: uuid.UUID, metadata: dict) -> None:
    db.add(
        AuditLog(
            actor_user_id=user_id,
            target_user_id=user_id,
            action=AuditAction.PLAN_CHANGED,
            log_metadata=metadata,
            created_at=utc_now(),
        )
    )


def get_active_plan(db: Session, user_id: uuid.UUID) -> PersonalPlan:
    plan = db.scalar(
        select(PersonalPlan)
        .options(selectinload(PersonalPlan.rules))
        .where(PersonalPlan.user_id == user_id, PersonalPlan.is_active.is_(True))
    )
    if plan is None:
        raise PersonalPlanNotFound(str(user_id))
    return plan


def get_active_plan_for_relationship(db: Session, relationship: TrustedPersonRelationship) -> PersonalPlan:
    """
    Usado pela pessoa de confiança com `ACCESS_CRISIS_PLAN` concedida
    (nível 5 do documento — "crise: acessar plano previamente
    autorizado"). Sempre disponível a quem tem a permissão, não só
    durante um estado VERMELHO: o próprio ponto de um plano estilo
    WRAP é a pessoa de apoio já conhecer o conteúdo ANTES de precisar
    dele, não descobri-lo no meio de uma crise.
    """
    return get_active_plan(db, relationship.owner_user_id)


def create_plan(db: Session, user: User, data: dict) -> PersonalPlan:
    existing = db.scalar(select(PersonalPlan).where(PersonalPlan.user_id == user.id, PersonalPlan.is_active.is_(True)))
    if existing is not None:
        raise PersonalPlanAlreadyExists(str(user.id))

    plan = PersonalPlan(user_id=user.id, is_active=True, **data)
    db.add(plan)
    _log(db, user.id, {"event": "plan_created"})
    db.commit()
    db.refresh(plan)
    return plan


def update_plan(db: Session, user: User, changes: dict) -> PersonalPlan:
    plan = get_active_plan(db, user.id)
    for field, value in changes.items():
        setattr(plan, field, value)
    _log(db, user.id, {"event": "plan_updated", "fields": list(changes.keys())})
    db.commit()
    db.refresh(plan)
    return plan


def _get_latest_plan(db: Session, user_id: uuid.UUID) -> PersonalPlan | None:
    return db.scalar(
        select(PersonalPlan)
        .options(selectinload(PersonalPlan.rules))
        .where(PersonalPlan.user_id == user_id)
        .order_by(PersonalPlan.created_at.desc())
        .limit(1)
    )


def deactivate_plan(db: Session, user: User) -> PersonalPlan:
    """
    Idempotente de verdade — mesmo padrão de
    `discontinue_medication`/`revoke_relationship`: busca o plano mais
    recente do usuário SEM filtrar por `is_active` (diferente de
    `get_active_plan`, usado por criar/editar/adicionar regra, que
    precisa mesmo de um plano ativo pra fazer sentido). Bug encontrado
    e corrigido durante o teste desta própria função: usar
    `get_active_plan` aqui fazia a segunda chamada não encontrar mais
    nada (já `is_active=False`) e devolver 404 — o oposto de idempotente.
    """
    plan = _get_latest_plan(db, user.id)
    if plan is None:
        raise PersonalPlanNotFound(str(user.id))
    if plan.is_active:
        plan.is_active = False
        _log(db, user.id, {"event": "plan_deactivated"})
        db.commit()
        db.refresh(plan)
    return plan


def add_rule(db: Session, user: User, signal_key: PersonalPlanSignal, threshold_description: str) -> PersonalPlanRule:
    plan = get_active_plan(db, user.id)  # 404 se não houver plano ativo — regra não existe solta
    rule = PersonalPlanRule(
        plan_id=plan.id, signal_key=signal_key, threshold_description=threshold_description, is_active=True
    )
    db.add(rule)
    _log(db, user.id, {"event": "rule_added", "signal_key": signal_key.value})
    db.commit()
    db.refresh(rule)
    return rule


def _get_rule_for_user(db: Session, user: User, rule_id: uuid.UUID) -> PersonalPlanRule:
    rule = db.scalar(
        select(PersonalPlanRule)
        .join(PersonalPlan, PersonalPlanRule.plan_id == PersonalPlan.id)
        .where(PersonalPlanRule.id == rule_id, PersonalPlan.user_id == user.id)
    )
    if rule is None:
        raise PersonalPlanRuleNotFound(str(rule_id))
    return rule


def update_rule(db: Session, user: User, rule_id: uuid.UUID, changes: dict) -> PersonalPlanRule:
    rule = _get_rule_for_user(db, user, rule_id)
    for field, value in changes.items():
        setattr(rule, field, value)
    _log(db, user.id, {"event": "rule_updated", "rule_id": str(rule_id)})
    db.commit()
    db.refresh(rule)
    return rule
