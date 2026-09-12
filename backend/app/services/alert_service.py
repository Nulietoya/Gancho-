"""
Modelo de estado (ETAPA 19, item 20). Lê os `DeviationEvent`s
produzidos pelos 4 motores (ETAPA 18) — nunca recalcula desvio aqui,
nunca lê indicador/baseline diretamente — e decide o estado atual do
usuário: VERDE (funcionamento habitual), AMARELO (deterioração
sustentada em uma área) ou VERMELHO (deterioração convergindo em
várias áreas ao mesmo tempo).

Por que não um limiar clínico: o documento de referência é explícito
(item 20) que regras têm que ser transparentes e configuráveis, nunca
inventar limiar clínico — e VERMELHO no documento inclui sintomas que
nenhum dado comportamental deste sistema consegue inferir (ideação
suicida, sintomas psicóticos/maníacos). Este motor nunca declara isso
sozinho; o que ele consegue defender com os dados que tem é
"deterioração convergindo em várias áreas ao mesmo tempo" (item 14:
"Faça isso simultaneamente em seis domínios e aparece algo muito mais
interessante"), que é justamente o critério de VERMELHO aqui. Um
`PersonalPlanSignal`/plano de crise definido pelo próprio usuário
(item 19, ainda não implementado) é o jeito correto de capturar
sinais que só a pessoa sabe reconhecer em si mesma — quando existir,
soma-se a este motor, nunca o substitui.

Nunca sobrescreve um "estado atual": cada mudança de estado é uma
linha nova em `Alert` (mesmo padrão de `TaskEvent`/`RoutineEvent`) —
o estado atual é sempre a linha mais recente. Reavaliar sem mudança
de estado não cria linha nova (evita ruído no histórico).

Notificar o dono e a rede de confiança quando o estado muda
(`RECEIVE_ALERT_YELLOW`/`RECEIVE_ALERT_RED`, modelados desde a ETAPA 7)
é responsabilidade de `notification_service` (ETAPA 22) — chamado
daqui só na transição de verdade (nunca em toda reavaliação sem
mudança), pra não duplicar a regra de "só quando muda" que já existe
pra gravar o `Alert`. `POST /alerts/sync` continua podendo ser
disparado manualmente, mas a partir da ETAPA 22 também roda sozinho
todo dia via `scheduler_service.run_nightly_cycle`.
"""
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AlertNotFound
from app.core.time import utc_now as _now
from app.models.audit import AuditLog
from app.models.deviation import Alert, DeviationEvent
from app.models.enums import AlertState, AuditAction, DeviationEngine
from app.models.user import User
from app.services import notification_service
from app.services.labels import ENGINE_LABELS

RECENT_WINDOW_DAYS = 7
RED_MIN_ENGINES = 2


def list_active_deviation_events(db: Session, user: User) -> list[DeviationEvent]:
    """
    Um `DeviationEvent` por motor, o mais recente, só se ainda dentro
    da janela de relevância — um desvio detectado há duas semanas não
    deveria manter alguém em AMARELO pra sempre (mesmo raciocínio de
    `recalibrate_baseline`: dado velho não pode classificar o presente
    eternamente). Público (não só uso interno de `evaluate_current_state`)
    porque a ETAPA 20 (explicabilidade) precisa exatamente desta mesma
    lista pra montar a explicação do estado atual — nunca recalcula
    nada, só reusa.
    """
    window_start = _now() - timedelta(days=RECENT_WINDOW_DAYS)
    latest_by_engine: dict[DeviationEngine, DeviationEvent] = {}
    rows = db.scalars(
        select(DeviationEvent)
        .where(DeviationEvent.user_id == user.id, DeviationEvent.detected_at >= window_start)
        .order_by(DeviationEvent.detected_at.desc())
    )
    for row in rows:
        latest_by_engine.setdefault(row.engine, row)
    return list(latest_by_engine.values())


def _reason_summary(state: AlertState, active_events: list[DeviationEvent]) -> str:
    if state == AlertState.GREEN:
        return f"Sem mudança persistente detectada nos últimos {RECENT_WINDOW_DAYS} dias."

    labels = [ENGINE_LABELS.get(e.engine, e.engine.value) for e in active_events]
    areas = ", ".join(labels)
    if state == AlertState.YELLOW:
        return f"Mudança sustentada no seu padrão em uma área: {areas}."
    return f"Mudança sustentada no seu padrão em {len(active_events)} áreas ao mesmo tempo: {areas}."


def evaluate_current_state(db: Session, user: User) -> tuple[AlertState, str, uuid.UUID | None]:
    active_events = list_active_deviation_events(db, user)

    if not active_events:
        return AlertState.GREEN, _reason_summary(AlertState.GREEN, []), None

    state = AlertState.RED if len(active_events) >= RED_MIN_ENGINES else AlertState.YELLOW
    # representa o alerta pelo desvio de maior magnitude entre os motores ativos
    triggering = max(active_events, key=lambda e: e.magnitude)
    return state, _reason_summary(state, active_events), triggering.id


def get_current_alert(db: Session, user: User) -> Alert | None:
    return db.scalar(
        select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc()).limit(1)
    )


def sync_alert_state(db: Session, user: User) -> Alert:
    """
    Reavalia o estado a partir dos `DeviationEvent`s recentes. Só
    grava uma linha nova em `Alert` quando o estado calculado é
    diferente do atual — reavaliar sem mudança nenhuma devolve o
    `Alert` existente, sem duplicar histórico.
    """
    state, reason_summary, triggering_deviation_id = evaluate_current_state(db, user)
    current = get_current_alert(db, user)

    if current is not None and current.state == state:
        return current

    alert = Alert(
        user_id=user.id,
        state=state,
        triggering_deviation_id=triggering_deviation_id,
        reason_summary=reason_summary,
        # setado explicitamente (não confia só no server_default): dentro de
        # uma mesma transação SQL, now() do Postgres fica congelado no
        # início da transação, o que quebraria a ordenação entre dois
        # `Alert`s criados na mesma transação (mesmo padrão já usado em
        # `DeviationEvent.detected_at`/`BaselineMetric.computed_at`).
        created_at=_now(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    if state == AlertState.RED:
        # Item 31: só a TRANSIÇÃO pra VERMELHO gera auditoria própria
        # (`AuditAction.CRITICAL_ALERT`, enum existia desde o início,
        # nunca gravado até a ETAPA 26) — nunca em toda reavaliação,
        # mesma regra de "só quando muda de verdade" que já governa a
        # criação da linha em `Alert` alguns passos acima.
        db.add(
            AuditLog(
                actor_user_id=user.id,
                target_user_id=user.id,
                action=AuditAction.CRITICAL_ALERT,
                log_metadata={"alert_id": str(alert.id)},
                created_at=_now(),
            )
        )
        db.commit()

    notification_service.notify_alert_state_change(db, user, alert)
    return alert


def list_alert_history(db: Session, user: User, limit: int = 30) -> list[Alert]:
    stmt = select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def get_alert(db: Session, user: User, alert_id) -> Alert:
    alert = db.scalar(select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id))
    if alert is None:
        raise AlertNotFound(str(alert_id))
    return alert


def acknowledge_alert(db: Session, user: User, alert_id) -> Alert:
    """Idempotente — item 27: reconstruir a linha do tempo, marcar de novo não muda nada."""
    alert = get_alert(db, user, alert_id)
    if alert.acknowledged_at is None:
        alert.acknowledged_at = _now()
        db.commit()
        db.refresh(alert)
    return alert


def resolve_alert(db: Session, user: User, alert_id) -> Alert:
    """Idempotente, mesma lógica de `acknowledge_alert`."""
    alert = get_alert(db, user, alert_id)
    if alert.resolved_at is None:
        alert.resolved_at = _now()
        db.commit()
        db.refresh(alert)
    return alert
