"""
Ciclo de vida da conta — exportação e exclusão de dados (ETAPA 25,
item 53 — requisito de LGPD declarado como escopo de v1 desde a
ETAPA 1: minimização, consentimento, exportação, exclusão, auditoria).

Módulo separado de `auth_service` (que cuida de credencial/sessão) de
propósito: exportar dado toca praticamente todo domínio do produto
(check-in, rotina, medicação, indicador, baseline, alerta,
intervenção, plano pessoal, rede de confiança, notificação) — juntar
isso em `auth_service` obrigaria um módulo de autenticação a importar
o resto do sistema inteiro, o oposto da separação já seguida em todo
o projeto.

**Decisão de escopo registrada**: exclusão é sempre soft delete
(`User.deactivated_at`, já modelado desde a ETAPA 4 e checado em
login/token desde a ETAPA 6, mas nunca setado em lugar nenhum até
aqui) — a conta para de ser utilizável na hora (login/token existente
param de funcionar, mesma checagem de `AccountInactive` já usada pra
conta bloqueada), mas o dado não é apagado fisicamente. Apagamento
físico após o prazo de retenção legal é um job de expurgo separado,
fora do escopo de um MVP sem ainda um prazo de retenção definido pelo
usuário/produto — decisão explícita, não esquecimento, mesmo padrão
já usado pra verificação de e-mail (ETAPA 22) e `PersonalPlan` (agora
implementado aqui).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidAccountPassword, PersonalPlanNotFound, ProfileNotFound
from app.core.security import verify_password
from app.core.time import utc_now
from app.models.audit import AuditLog
from app.models.checkin import DailyCheckIn
from app.models.enums import AuditAction
from app.models.intervention import Intervention
from app.models.medication import Medication
from app.models.notification import Notification
from app.models.trust import TrustedPersonRelationship
from app.models.user import User
from app.schemas.checkin import CheckInPublic
from app.schemas.intervention import InterventionPublic
from app.schemas.medication import MedicationPublic
from app.schemas.notification import NotificationPublic
from app.schemas.personal_plan import PersonalPlanPublic
from app.schemas.profile import ProfilePublic
from app.schemas.trust import RelationshipPublic
from app.services import auth_service, personal_plan_service, profile_service, routine_service


def deactivate_account(db: Session, user: User, password: str) -> User:
    """
    Reconfirma a senha antes de uma ação que, na prática, é
    irreversível pro usuário (mesmo critério já usado em
    `auth_service.change_password`). Idempotente: chamar de novo numa
    conta já desativada não levanta erro, só devolve o estado atual —
    a pessoa não tem mais como se autenticar pra chamar isso duas
    vezes por engano de qualquer forma, mas evita um efeito colateral
    estranho se algum outro código chamar isso de novo.
    """
    if not verify_password(password, user.password_hash):
        raise InvalidAccountPassword()

    if user.deactivated_at is None:
        now = utc_now()
        user.is_active = False
        user.deactivated_at = now
        db.add(
            AuditLog(
                actor_user_id=user.id,
                target_user_id=user.id,
                action=AuditAction.ACCOUNT_DELETION_REQUESTED,
                log_metadata={},
                created_at=now,
            )
        )
        db.commit()
        auth_service.revoke_all_sessions(db, user)
        db.refresh(user)
    return user


def export_account_data(db: Session, user: User) -> dict:
    """
    Item 53 — portabilidade: um retrato dos dados que a própria conta
    gerou ou recebeu, direto em JSON (sem gerar arquivo/job assíncrono
    — volume esperado no MVP não justifica essa complexidade, item 65).
    Nunca inclui credencial (hash de senha, token) nem o e-mail/nome
    de outra pessoa (rede de confiança aparece só pelo `relationship_id`
    e rótulo que o próprio usuário deu, já visível em
    `GET /trusted-people`).
    """
    try:
        profile = ProfilePublic.model_validate(profile_service.get_profile(db, user)).model_dump(mode="json")
    except ProfileNotFound:
        profile = None

    checkins = [
        CheckInPublic.model_validate(c).model_dump(mode="json")
        for c in db.scalars(select(DailyCheckIn).where(DailyCheckIn.user_id == user.id))
    ]

    routine_history = [
        {
            "version": r.version,
            "period_start": r.period_start.isoformat(),
            "period_end": _as_str(r.period_end),
            "typical_wake_time": _as_str(r.typical_wake_time),
            "typical_sleep_time": _as_str(r.typical_sleep_time),
        }
        for r in routine_service.list_routine_history(db, user)
    ]
    life_events = [
        {
            "type": e.event_type.value,
            "start_date": e.start_date.isoformat(),
            "end_date": _as_str(e.end_date),
            "description": e.description,
        }
        for e in routine_service.list_life_events(db, user)
    ]

    medications = [
        MedicationPublic.model_validate(m).model_dump(mode="json")
        for m in db.scalars(select(Medication).where(Medication.user_id == user.id))
    ]

    interventions = [
        InterventionPublic.model_validate(i).model_dump(mode="json")
        for i in db.scalars(select(Intervention).where(Intervention.user_id == user.id))
    ]

    try:
        personal_plan = PersonalPlanPublic.model_validate(
            personal_plan_service.get_active_plan(db, user.id)
        ).model_dump(mode="json")
    except PersonalPlanNotFound:
        personal_plan = None

    trusted_relationships = [
        RelationshipPublic.model_validate(r).model_dump(mode="json")
        for r in db.scalars(
            select(TrustedPersonRelationship).where(TrustedPersonRelationship.owner_user_id == user.id)
        )
    ]

    notifications = [
        NotificationPublic.model_validate(n).model_dump(mode="json")
        for n in db.scalars(select(Notification).where(Notification.user_id == user.id))
    ]

    db.add(
        AuditLog(
            actor_user_id=user.id,
            target_user_id=user.id,
            action=AuditAction.DATA_EXPORTED,
            log_metadata={},
            created_at=utc_now(),
        )
    )
    db.commit()

    return {
        "account": {"id": str(user.id), "email": user.email, "created_at": user.created_at.isoformat()},
        "profile": profile,
        "checkins": checkins,
        "routine_history": routine_history,
        "life_events": life_events,
        "medications": medications,
        "interventions": interventions,
        "personal_plan": personal_plan,
        "trusted_relationships": trusted_relationships,
        "notifications": notifications,
    }


def _as_str(value) -> str | None:
    return value.isoformat() if value is not None else None
