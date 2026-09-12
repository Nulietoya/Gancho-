"""
Intervenções (ETAPA 21, itens 17/23/24/26 do documento de referência):
microintervenção sugerida (reduzir a tarefa ao menor passo possível,
timer curto, contato social breve, ...) ou sessão de body doubling
com uma pessoa de confiança. Os models (`Intervention`,
`InterventionResult`) já existiam desde a ETAPA 4 — verificado ao
vivo contra o Postgres antes de começar, sem migration nova aqui.

**Decisão de escopo registrada**: diferente de `Task`/`Routine`, uma
intervenção não ganha uma tabela de evento própria. O documento não
pede histórico auditável rico por intervenção (o que importa é
"ajudou ou não", registrado em `InterventionResult`) e o próprio
`status` + `updated_at` (herdado de `TimestampMixin`) já bastam pra
reconstruir quando cada transição aconteceu. Se isso deixar de ser
suficiente (por exemplo, pra medir quanto tempo uma sessão de body
doubling ficou parada em REQUESTED), um `InterventionEvent` fica fácil
de adicionar depois sem reescrever este módulo — mesma lógica de
"não complicar sem necessidade" já usada no resto do projeto.

**Decisão de máquina de estados** (item 17 — escada de escalonamento:
reduzir pra primeira ação → timer curto → body doubling → começar
imediatamente): friction mínima é o requisito central, porque a
própria pessoa pode procrastinar em começar uma intervenção pensada
pra ajudar a não procrastinar. Por isso `start` aceita partir de
SUGGESTED, REQUESTED ou ACCEPTED — uma microintervenção não precisa
passar por "pedir" e "aceitar" (não tem outra parte envolvida), então
o caminho SUGGESTED → STARTED direto é o caminho normal pra ela; body
doubling normalmente segue SUGGESTED → REQUESTED → ACCEPTED → STARTED,
mas nada aqui impede o atalho se a pessoa de confiança já topou por
fora do app. `dismiss` aceita partir de qualquer estado não-terminal —
desistir de uma intervenção nunca é um erro nem gera fricção extra
(tom de voz do produto: nunca "você falhou de novo").

**HELP_WITH_TASK, finalmente com uso real**: registrada como "sem uso
por ora" na decisão da ETAPA 10, é a permissão que agora gate a ação
de uma pessoa de confiança aceitar um pedido de body doubling
endereçado a ela (`accept_intervention_by_trusted_person`).
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import InterventionNotFound, InvalidInterventionTransition
from app.core.time import utc_now as _now
from app.models.enums import InterventionStatus, InterventionType, NotificationPriority, NotificationType
from app.models.intervention import Intervention, InterventionResult
from app.models.trust import TrustedPersonRelationship
from app.models.user import User
from app.services import deviation_service, notification_service, task_service, trust_service

# Catálogo de microintervenções (item 24) — texto descreve a ação em
# si, nunca um julgamento sobre a pessoa não ter feito sozinha.
_MICROINTERVENTION_CATALOG: list[str] = [
    "Reduza para a menor ação possível: só o primeiro passo, não a tarefa inteira.",
    "Ligue um timer de 5 minutos e faça só até ele tocar — pode parar depois, sem culpa.",
    "Mande uma mensagem curta pra alguém antes de começar, só pra avisar que vai tentar agora.",
    "Retome só a rotina mínima de hoje (uma coisa básica), sem tentar recuperar o resto do dia.",
    "Comece separando o que precisa antes de decidir se vai fazer ou não a tarefa em si.",
]

_BODY_DOUBLING_TEXT = (
    "Peça para uma pessoa de confiança ficar por perto — presencialmente ou numa "
    "chamada — enquanto você faz a tarefa. Ela não precisa ajudar de fato, só estar lá."
)

# De quais status cada ação pode partir — ver docstring do módulo
# pra justificativa de cada uma.
_ALLOWED_FROM: dict[str, set[InterventionStatus]] = {
    "request": {InterventionStatus.SUGGESTED},
    "accept": {InterventionStatus.REQUESTED},
    "start": {InterventionStatus.SUGGESTED, InterventionStatus.REQUESTED, InterventionStatus.ACCEPTED},
    "finish": {InterventionStatus.STARTED},
    "dismiss": {
        InterventionStatus.SUGGESTED,
        InterventionStatus.REQUESTED,
        InterventionStatus.ACCEPTED,
        InterventionStatus.STARTED,
    },
}


def _pick_microintervention_text(db: Session, user_id: uuid.UUID) -> str:
    """
    Roda pelo catálogo em vez de repetir sempre a primeira sugestão —
    determinístico (conta quantas microintervenções esse usuário já
    recebeu) em vez de aleatório, pra ficar testável sem precisar
    mockar sorteio.
    """
    count = db.scalar(
        select(func.count(Intervention.id)).where(
            Intervention.user_id == user_id, Intervention.type == InterventionType.MICROINTERVENTION
        )
    )
    index = (count or 0) % len(_MICROINTERVENTION_CATALOG)
    return _MICROINTERVENTION_CATALOG[index]


def suggest_intervention(
    db: Session,
    user: User,
    *,
    type: InterventionType = InterventionType.MICROINTERVENTION,
    related_task_id: uuid.UUID | None = None,
    related_deviation_id: uuid.UUID | None = None,
) -> Intervention:
    """
    Cria a intervenção em SUGGESTED. Disparado manualmente por
    enquanto (o próprio usuário pede uma sugestão, ou o frontend
    chama isso a partir de uma tarefa/evento de desvio específico);
    vira automático — encadeado a `DeviationEvent`/`Alert` — na
    ETAPA 22, junto do job noturno.
    """
    if related_task_id is not None:
        task_service.get_task(db, user, related_task_id)  # 404 se a tarefa não existir/não for do usuário
    if related_deviation_id is not None:
        deviation_service.get_deviation_event(db, user, related_deviation_id)  # idem

    suggestion_text = (
        _BODY_DOUBLING_TEXT
        if type == InterventionType.BODY_DOUBLING_SESSION
        else _pick_microintervention_text(db, user.id)
    )

    intervention = Intervention(
        user_id=user.id,
        type=type,
        status=InterventionStatus.SUGGESTED,
        related_task_id=related_task_id,
        related_deviation_id=related_deviation_id,
        suggestion_text=suggestion_text,
    )
    db.add(intervention)
    db.commit()
    db.refresh(intervention)
    return intervention


def get_intervention(db: Session, user: User, intervention_id: uuid.UUID) -> Intervention:
    intervention = db.scalar(
        select(Intervention).where(Intervention.id == intervention_id, Intervention.user_id == user.id)
    )
    if intervention is None:
        raise InterventionNotFound(str(intervention_id))
    return intervention


def list_interventions(
    db: Session, user: User, status_filter: InterventionStatus | None = None
) -> list[Intervention]:
    stmt = select(Intervention).where(Intervention.user_id == user.id).order_by(Intervention.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Intervention.status == status_filter)
    return list(db.scalars(stmt))


def _transition(db: Session, user: User, intervention_id: uuid.UUID, action: str) -> Intervention:
    intervention = get_intervention(db, user, intervention_id)
    if intervention.status not in _ALLOWED_FROM[action]:
        raise InvalidInterventionTransition(intervention.status.value, action)
    return intervention


def request_intervention(
    db: Session,
    user: User,
    intervention_id: uuid.UUID,
    support_relationship_id: uuid.UUID | None = None,
) -> Intervention:
    """
    `support_relationship_id` marca a quem o pedido de body doubling
    foi endereçado — validado como relacionamento do próprio dono
    (reusa `trust_service.get_relationship_for_owner`, que já levanta
    404 se não pertencer a ele). Nada aqui checa HELP_WITH_TASK: quem
    concede ou não a permissão é a pessoa de confiança, checado só
    quando ELA aceita (`accept_intervention_by_trusted_person`) —
    pedir não exige que a permissão já esteja concedida, só aceitar.
    """
    intervention = _transition(db, user, intervention_id, "request")
    relationship = None
    if support_relationship_id is not None:
        relationship = trust_service.get_relationship_for_owner(db, user, support_relationship_id)
        intervention.support_relationship_id = support_relationship_id
    intervention.status = InterventionStatus.REQUESTED
    db.commit()
    db.refresh(intervention)

    # ETAPA 22: avisa a pessoa de confiança específica que foi
    # endereçada — só ela, nunca uma notificação genérica pra toda a
    # rede (mesmo escopo do próprio pedido).
    if relationship is not None and relationship.trusted_user_id is not None:
        notification_service.create_notification(
            db,
            relationship.trusted_user_id,
            NotificationType.SUPPORT_REQUEST,
            NotificationPriority.MEDIUM,
            {
                "intervention_id": str(intervention.id),
                "relationship_id": str(relationship.id),
                "message": "Alguém que confia em você pediu companhia (body doubling) para uma tarefa.",
            },
        )
    return intervention


def start_intervention(db: Session, user: User, intervention_id: uuid.UUID) -> Intervention:
    intervention = _transition(db, user, intervention_id, "start")
    intervention.status = InterventionStatus.STARTED
    db.commit()
    db.refresh(intervention)
    return intervention


def finish_intervention(db: Session, user: User, intervention_id: uuid.UUID) -> Intervention:
    intervention = _transition(db, user, intervention_id, "finish")
    intervention.status = InterventionStatus.FINISHED
    db.commit()
    db.refresh(intervention)
    return intervention


def dismiss_intervention(db: Session, user: User, intervention_id: uuid.UUID) -> Intervention:
    intervention = _transition(db, user, intervention_id, "dismiss")
    intervention.status = InterventionStatus.DISMISSED
    db.commit()
    db.refresh(intervention)
    return intervention


def accept_intervention_by_trusted_person(
    db: Session, relationship: TrustedPersonRelationship, intervention_id: uuid.UUID
) -> Intervention:
    """
    Chamado pela pessoa de confiança, nunca pelo dono. `relationship`
    já chega autorizado (a rota depende de
    `require_relationship_permission(PermissionKey.HELP_WITH_TASK)`) —
    mas isso só prova que ELA tem a permissão, não que ESTE pedido foi
    endereçado a ela. Por isso a busca abaixo filtra também por
    `support_relationship_id == relationship.id`: um pedido endereçado
    a outra pessoa de confiança devolve 404 aqui, igual a um
    `relationship_id` inexistente (mesmo princípio "404 não 403" usado
    no resto da camada de autorização).
    """
    intervention = db.scalar(
        select(Intervention).where(
            Intervention.id == intervention_id,
            Intervention.support_relationship_id == relationship.id,
        )
    )
    if intervention is None:
        raise InterventionNotFound(str(intervention_id))
    if intervention.status not in _ALLOWED_FROM["accept"]:
        raise InvalidInterventionTransition(intervention.status.value, "accept")

    intervention.status = InterventionStatus.ACCEPTED
    db.commit()
    db.refresh(intervention)
    return intervention


def record_result(
    db: Session,
    user: User,
    intervention_id: uuid.UUID,
    helped: bool | None,
    user_note: str | None,
) -> InterventionResult:
    """
    Só permitido depois de FINISHED — "ajudou ou não" é avaliado sobre
    algo que de fato aconteceu, nunca sobre uma intervenção ainda
    sugerida/pedida. Upsert: chamar de novo atualiza o mesmo registro
    (a pessoa pode reavaliar depois), nunca duplica — `InterventionResult`
    tem `intervention_id` único no banco.
    """
    intervention = get_intervention(db, user, intervention_id)
    if intervention.status != InterventionStatus.FINISHED:
        raise InvalidInterventionTransition(intervention.status.value, "record_result")

    now = _now()
    if intervention.result is not None:
        intervention.result.helped = helped
        intervention.result.user_note = user_note
        intervention.result.recorded_at = now
        result = intervention.result
    else:
        result = InterventionResult(
            intervention_id=intervention.id, helped=helped, user_note=user_note, recorded_at=now
        )
        db.add(result)

    db.commit()
    db.refresh(result)
    return result
