"""
Rótulos em português usados nas explicações do motor de desvio
(ETAPA 18) e do modelo de estado (ETAPA 19) — centralizados aqui pra
nunca ter duas strings diferentes pro mesmo motor/indicador em
lugares diferentes, e pra ETAPA 20 (explicabilidade) reusar
exatamente o mesmo vocabulário que já aparece nas explicações
geradas por essas duas etapas.
"""
from app.models.enums import DeviationEngine, IndicatorKey

ENGINE_LABELS: dict[DeviationEngine, str] = {
    DeviationEngine.EXECUTIVE: "execução de tarefas",
    DeviationEngine.AVOIDANCE: "evitação",
    DeviationEngine.ACTIVATION: "ativação",
    DeviationEngine.STABILITY: "estabilidade",
}

INDICATOR_LABELS: dict[IndicatorKey, str] = {
    IndicatorKey.TASKS_STARTED_COUNT: "o número de tarefas que você começou",
    IndicatorKey.TASKS_COMPLETED_COUNT: "o número de tarefas que você concluiu",
    IndicatorKey.TASKS_POSTPONED_COUNT: "o número de tarefas adiadas",
    IndicatorKey.ABILITY_TO_START_TASKS: "sua capacidade percebida de começar tarefas",
    IndicatorKey.ANXIETY: "seu nível de ansiedade",
    IndicatorKey.ENERGY: "sua energia",
    IndicatorKey.MEDICATION_ADHERENCE: "sua adesão à medicação",
    IndicatorKey.MOOD: "seu humor",
    IndicatorKey.SLEEP_QUALITY: "sua qualidade de sono",
}
