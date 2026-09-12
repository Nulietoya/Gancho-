"""
Explicabilidade (ETAPA 20, itens 15/22). Este módulo não calcula
nada novo — nunca reabre baseline, nunca recalcula z-score ou estado
— só organiza o que a ETAPA 18 (`DeviationEvent`) e a ETAPA 19
(`Alert`) já calcularam numa forma navegável, com a mesma
justificativa do item 15 ("descobrir o gargalo": ao invés de só dizer
"você mudou", mostrar exatamente qual indicador, comparado com qual
baseline, por quantos dias) e do item 22 (nenhum alerta sem
explicação).

Uma explicação de motor único (`explain_deviation_event`) é sempre
fiel ao momento em que aquele `DeviationEvent` foi calculado — o
`baseline_snapshot` já é um retrato congelado. Já a explicação de um
`Alert` (`explain_alert`) é montada a partir dos `DeviationEvent`s
**atualmente** dentro da janela de relevância (mesma função que
`alert_service.sync_alert_state` usa) — não uma reconstrução
retroativa exata do instante em que aquele `Alert` foi criado, porque
`Alert` guarda só um `DeviationEvent` representante, não a lista
completa de motores ativos naquele momento. Decisão de escopo
registrada: para um histórico auditável exato por `Alert`, seria
preciso guardar a lista completa de eventos convergentes em cada
transição — reavaliar quando isso importar de verdade.
"""
from sqlalchemy.orm import Session

from app.models.enums import DeviationEngine
from app.models.user import User
from app.schemas.explainability import AlertExplanation, EngineExplanation
from app.services import alert_service


def explain_deviation_event(event) -> EngineExplanation:
    return EngineExplanation.from_deviation_event(event)


def explain_alert(db: Session, user: User, alert) -> AlertExplanation:
    active_events = alert_service.list_active_deviation_events(db, user)
    return AlertExplanation.from_alert(alert, active_events, total_engines=len(DeviationEngine))
