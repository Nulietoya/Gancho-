"""
Motor de desvio (ETAPA 18, itens 9-12/14/20/22). Lê exclusivamente
`Baseline`/`BaselineMetric`/`FunctionalIndicator` — nunca dado bruto
de check-in/tarefa/medicação diretamente, pelo mesmo motivo já
registrado em `baseline_service`: o motor analítico tem que poder ser
trocado sem reescrever o resto do produto (item 38).

Quatro motores separados (item 9-12), nunca um índice único: cada um
olha só pros indicadores que fazem sentido pra ele. A tabela abaixo é
uma decisão de escopo explícita — o documento de referência descreve
listas de sinais mais ricas por motor (sono, saída de casa, contato
social, carga de evitação...) mas esses indicadores ainda não têm
fonte de dado real (registrado em `indicator_service`), então cada
motor usa só os indicadores que hoje são alimentados de verdade. Como
o `FunctionalIndicator` é o único ponto de acoplamento, adicionar um
sinal novo a um motor no futuro é só acrescentar uma linha em
`ENGINE_INDICATORS`, nunca reescrever a lógica de detecção.

    EXECUTIVO   — tarefas iniciadas/concluídas (queda = ruim),
                  tarefas adiadas (alta = ruim), capacidade percebida
                  de começar tarefas (queda = ruim).
    EVITAÇÃO    — ansiedade (alta = ruim); proxy de "preocupação
                  antecipatória" até existir um indicador dedicado de
                  evitação (`AVOIDANCE_LOAD`, sem fonte ainda).
    ATIVAÇÃO    — energia (queda = ruim); proxy até `LEFT_HOME` /
                  `SOCIAL_CONTACT` / `ACTIVITY_LEVEL` terem fonte real.
    ESTABILIDADE — adesão a medicação (queda = ruim), humor (queda =
                  ruim), qualidade de sono autodeclarada (queda =
                  ruim) — mudança de sono é sinal de alerta que o
                  próprio usuário já reconhece no plano pessoal
                  (`PersonalPlanSignal.SONO`); tratada aqui como parte
                  da estabilidade geral, não de um motor à parte,
                  porque a relação sono↔funcionamento é bidirecional
                  e inespecífica (não aponta sozinha pra evitação
                  nem pra déficit executivo).

Cada indicador do motor é avaliado assim:
1. Baseline precisa existir e ter pelo menos `MIN_BASELINE_SAMPLE`
   dias de amostra — item 20: nunca inventar limiar clínico, mas
   também nunca decidir em cima de dado de menos (poucos check-ins
   não sustentam média/desvio padrão confiáveis).
2. Sem variabilidade (`stddev` None ou 0) não dá pra calcular
   z-score — o indicador é ignorado nesse ciclo, nunca tratado como
   "sem desvio" nem "desvio infinito".
3. A partir do dia mais recente com dado, anda pra trás contando
   quantos dias seguidos o valor (ajustado por direção) passa de
   `Z_THRESHOLD` desvios-padrão do baseline. Indicador de contagem
   (tarefas) trata dia sem registro como zero de verdade — ausência
   de evento de tarefa É zero atividade; indicador subjetivo/adesão
   trata dia sem registro como buraco que quebra a sequência (não dá
   pra supor o valor de um check-in que não foi feito).
4. Só vira sinal se a sequência atingir `MIN_DURATION_DAYS` — item 1:
   nunca por dia isolado, sempre desvio persistente.

Um `DeviationEvent` só é criado se pelo menos um indicador do motor
convergiu (domains_count > 0) — itens com um só indicador mapeado
(Evitação, Ativação, hoje) precisam poder disparar sozinhos, dado que
não têm ainda um segundo sinal real pra exigir convergência entre
domínios; quando esse segundo sinal existir, `convergence_score`
(domains_count / total avaliado) já fica pronto pra distinguir "um
sinal isolado" de "vários sinais junto" sem mexer no motor.

Este módulo produz só o `DeviationEvent`, por motor. A leitura
combinada dos quatro motores que decide o estado verde/amarelo/
vermelho do usuário (`Alert`) é escopo da ETAPA 19 — de propósito
fora daqui, mesmo raciocínio de separar `recompute`/`recalibrate` em
`baseline_service`.
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BaselineNotFound, DeviationEventNotFound, NoIndicatorData
from app.core.time import utc_now as _now
from app.models.baseline import FunctionalIndicator
from app.models.deviation import DeviationEvent
from app.models.enums import DeviationEngine, IndicatorKey
from app.models.user import User
from app.services import baseline_service
from app.services.labels import INDICATOR_LABELS

Z_THRESHOLD = 1.5
MIN_BASELINE_SAMPLE = 5
MIN_DURATION_DAYS = 3
_MAX_STREAK_LOOKBACK = 60  # segurança contra loop indefinido em indicador de contagem sempre zerado

# direção: +1 = "subir é ruim", -1 = "descer é ruim" — multiplicado pelo
# z-score dá sempre um número positivo quando o dia é "ruim" na direção certa.
ENGINE_INDICATORS: dict[DeviationEngine, list[tuple[IndicatorKey, int]]] = {
    DeviationEngine.EXECUTIVE: [
        (IndicatorKey.TASKS_STARTED_COUNT, -1),
        (IndicatorKey.TASKS_COMPLETED_COUNT, -1),
        (IndicatorKey.TASKS_POSTPONED_COUNT, 1),
        (IndicatorKey.ABILITY_TO_START_TASKS, -1),
    ],
    DeviationEngine.AVOIDANCE: [
        (IndicatorKey.ANXIETY, 1),
    ],
    DeviationEngine.ACTIVATION: [
        (IndicatorKey.ENERGY, -1),
    ],
    DeviationEngine.STABILITY: [
        (IndicatorKey.MEDICATION_ADHERENCE, -1),
        (IndicatorKey.MOOD, -1),
        (IndicatorKey.SLEEP_QUALITY, -1),
    ],
}

# Indicadores de contagem: ausência de registro no dia é um zero real
# (nenhum evento de tarefa aconteceu), não "sem dado".
_COUNT_INDICATORS = {
    IndicatorKey.TASKS_STARTED_COUNT,
    IndicatorKey.TASKS_POSTPONED_COUNT,
    IndicatorKey.TASKS_COMPLETED_COUNT,
}

def _latest_metric(baseline):
    return max(baseline.metrics, key=lambda m: m.computed_at, default=None)


def _evaluate_indicator(db: Session, user: User, indicator_key: IndicatorKey, direction: int) -> dict | None:
    """
    Devolve None quando não há baseline confiável, sem variabilidade,
    ou a sequência de dias ruins não atinge o mínimo — nesses casos o
    indicador simplesmente não participa do desvio deste ciclo. Só
    devolve um resultado quando encontra desvio persistente de verdade.
    """
    try:
        baseline = baseline_service.get_active_baseline(db, user, indicator_key)
    except BaselineNotFound:
        return None

    metric = _latest_metric(baseline)
    if metric is None or metric.sample_size < MIN_BASELINE_SAMPLE:
        return None
    if metric.stddev is None or metric.stddev == 0:
        return None

    is_count = indicator_key in _COUNT_INDICATORS
    window_start = date.today() - timedelta(days=_MAX_STREAK_LOOKBACK)
    rows = db.scalars(
        select(FunctionalIndicator).where(
            FunctionalIndicator.user_id == user.id,
            FunctionalIndicator.indicator_key == indicator_key,
            FunctionalIndicator.recorded_for_date >= window_start,
        )
    )
    values_by_date: dict[date, float] = {row.recorded_for_date: row.value for row in rows}

    if is_count:
        anchor = date.today()
    else:
        if not values_by_date:
            return None
        anchor = max(values_by_date)

    streak_days = 0
    day = anchor
    while streak_days < _MAX_STREAK_LOOKBACK:
        if day in values_by_date:
            value = values_by_date[day]
        elif is_count:
            value = 0.0
        else:
            break  # buraco em indicador subjetivo/adesão quebra a sequência

        z = (value - metric.mean) / metric.stddev
        z_bad = z * direction
        if z_bad < Z_THRESHOLD:
            break

        streak_days += 1
        day -= timedelta(days=1)

    if streak_days < MIN_DURATION_DAYS:
        return None

    recent_z_bad = ((metric.recent_value - metric.mean) / metric.stddev) * direction
    return {
        "indicator_key": indicator_key,
        "streak_days": streak_days,
        "mean": metric.mean,
        "stddev": metric.stddev,
        "recent_value": metric.recent_value,
        "z_bad_recent": recent_z_bad,
    }


def _build_explanation(triggered: list[dict]) -> str:
    """
    Item 22: nenhum alerta sem explicação. Item da sessão anterior
    sobre tom de voz: descreve mudança de padrão, nunca rótulo
    clínico — "sua rotina mudou", nunca "você está entrando em
    depressão/crise".
    """
    parts = []
    for t in triggered:
        label = INDICATOR_LABELS.get(t["indicator_key"], t["indicator_key"].value)
        parts.append(f"{label} mudou por {t['streak_days']} dia(s) seguidos em relação ao seu padrão habitual")
    return "Sua rotina mudou: " + "; ".join(parts) + "."


def run_engine(db: Session, user: User, engine: DeviationEngine) -> DeviationEvent | None:
    """
    Recalcula o baseline de cada indicador mapeado pro motor (garante
    que o motor sempre olha pro número mais fresco possível — ainda
    não existe job noturno, ETAPA 22, então essa chamada é o que
    mantém o baseline em dia) e então avalia desvio persistente. Só
    cria e devolve um `DeviationEvent` se pelo menos um indicador
    convergiu; caso contrário devolve None sem tocar no banco.
    """
    mapped = ENGINE_INDICATORS[engine]
    total_evaluated = len(mapped)
    triggered: list[dict] = []

    for indicator_key, direction in mapped:
        try:
            baseline_service.recompute_baseline(db, user, indicator_key)
        except NoIndicatorData:
            continue
        result = _evaluate_indicator(db, user, indicator_key, direction)
        if result is not None:
            triggered.append(result)

    if not triggered:
        return None

    domains_count = len(triggered)
    duration_days = min(t["streak_days"] for t in triggered)
    magnitude = max(abs(t["z_bad_recent"]) for t in triggered)
    convergence_score = domains_count / total_evaluated if total_evaluated else None

    baseline_snapshot = {
        t["indicator_key"].value: {
            "mean": t["mean"],
            "stddev": t["stddev"],
            "recent_value": t["recent_value"],
            "streak_days": t["streak_days"],
        }
        for t in triggered
    }

    event = DeviationEvent(
        user_id=user.id,
        engine=engine,
        detected_at=_now(),
        magnitude=magnitude,
        duration_days=duration_days,
        domains_count=domains_count,
        convergence_score=convergence_score,
        triggering_indicator_keys=[t["indicator_key"].value for t in triggered],
        baseline_snapshot=baseline_snapshot,
        explanation=_build_explanation(triggered),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def run_all_engines(db: Session, user: User) -> list[DeviationEvent]:
    events = []
    for engine in DeviationEngine:
        event = run_engine(db, user, engine)
        if event is not None:
            events.append(event)
    return events


def list_deviation_events(
    db: Session,
    user: User,
    engine: DeviationEngine | None = None,
    limit: int = 30,
) -> list[DeviationEvent]:
    stmt = select(DeviationEvent).where(DeviationEvent.user_id == user.id)
    if engine is not None:
        stmt = stmt.where(DeviationEvent.engine == engine)
    stmt = stmt.order_by(DeviationEvent.detected_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def get_deviation_event(db: Session, user: User, event_id) -> DeviationEvent:
    event = db.scalar(
        select(DeviationEvent).where(DeviationEvent.id == event_id, DeviationEvent.user_id == user.id)
    )
    if event is None:
        raise DeviationEventNotFound(str(event_id))
    return event
