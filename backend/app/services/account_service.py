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

**Decisão de escopo original (ETAPA 25) revertida em 2026-09-22**:
exclusão era sempre soft delete (`User.deactivated_at`) — a conta
parava de ser utilizável, mas o dado não era apagado fisicamente,
com apagamento físico adiado pra um job de expurgo futuro sem prazo
de retenção definido. Revertido a pedido do usuário: (1) contas de
teste acumuladas durante QA precisavam de limpeza de verdade — soft
delete nem libera o e-mail pra reuso (`User.email` é `unique`) nem
reduz dado nenhum no banco; (2) numa app que lida com dado de saúde
mental (check-in de humor, medicação, observação de terceiro), dar
ao usuário real exclusão definitiva de verdade, sob pedido explícito,
é mais alinhado a privacidade/LGPD do que só desativação. `is_active`/
`deactivated_at` continuam no modelo `User` (não removidos — servem
pra qualquer suspensão futura que não seja exclusão, ex.: bloqueio
administrativo), só não são mais tocados por este fluxo.

`delete_account` é apagamento físico de verdade (`DELETE FROM
users`), não um flag. Tudo que pertence à conta cai em cascata pelo
próprio schema (`ondelete="CASCADE"` já declarado em cada FK pra
`users.id` desde a migration inicial — check-in, tarefa, medicação,
rotina, plano pessoal, baseline, desvio, intervenção, notificação,
sessão/token, relacionamento em que a conta é a DONA). A exceção
deliberada é `AuditLog` (`ondelete="SET NULL"` em `actor_user_id`/
`target_user_id`): o registro de auditoria sobrevive à conta,
anonimizado, porque auditoria é "o que aconteceu", não "quem ainda
existe pra contar" — apagar o rastro junto pioraria a garantia que
auditoria existe pra dar. Pelo mesmo motivo, o `AuditLog` da própria
exclusão é gravado ANTES do `db.delete(user)`, na mesma transação.

Uma conta que é a PESSOA DE CONFIANÇA (não dona) de outros relaciona-
mentos é o único caso que o cascade puro deixaria errado: a FK
`trusted_user_id` é `ondelete="SET NULL"` (célula 14 do modelo — o
convite existe antes da conta existir, então já precisa aceitar nulo)
— sem tratamento manual, a linha sobreviveria com `trusted_user_id`
nulo mas `status` ainda "accepted", uma pessoa de confiança fantasma
que o dono continuaria vendo como ativa. Por isso `delete_account`
revoga esses relacionamentos explicitamente (mesmo efeito de
`trust_service.revoke_relationship`, sem repetir a consulta por dono
já que aqui a consulta é pelo lado da pessoa de confiança) antes de
apagar a conta.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidAccountPassword, PersonalPlanNotFound, ProfileNotFound
from app.core.security import verify_password
from app.core.time import utc_now
from app.models.audit import AuditLog
from app.models.checkin import DailyCheckIn
from app.models.enums import AuditAction, RelationshipStatus
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
from app.services import personal_plan_service, profile_service, routine_service


def delete_account(db: Session, user: User, password: str) -> None:
    """
    Reconfirma a senha antes de uma ação irreversível de verdade
    (mesmo critério já usado em `auth_service.change_password` e,
    antes, em `deactivate_account`) — aqui com peso maior ainda, já
    que não existe mais "desfazer depois".
    """
    if not verify_password(password, user.password_hash):
        raise InvalidAccountPassword()

    now = utc_now()

    as_trusted_person = db.scalars(
        select(TrustedPersonRelationship).where(
            TrustedPersonRelationship.trusted_user_id == user.id,
            TrustedPersonRelationship.status == RelationshipStatus.ACCEPTED,
        )
    ).all()
    for relationship in as_trusted_person:
        relationship.status = RelationshipStatus.REVOKED
        relationship.revoked_at = now

    db.add(
        AuditLog(
            actor_user_id=user.id,
            target_user_id=user.id,
            action=AuditAction.ACCOUNT_DELETED,
            log_metadata={},
            created_at=now,
        )
    )
    db.commit()

    db.delete(user)
    db.commit()


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
