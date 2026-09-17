"""
Dicas de estratégia de adesão a medicação. Pedido do usuário: quando o
MESMO motivo de não-adesão se repete, sugerir algo concreto em vez de
só registrar o motivo de novo. Nunca uma instrução de dose/horário —
item 13 é claro que nada aqui pode virar recomendação clínica; são
estratégias de HÁBITO (hábito-âncora, redução de barreira, deixar
visível), o tipo de intervenção comportamental com respaldo real na
literatura sobre adesão a medicação, nunca personalizada a nenhum dado
além do motivo que a própria pessoa já informou.

`DECISAO_PROPRIA` fica de propósito sem dica: quando a pessoa registra
que a decisão de não tomar foi dela, sugerir uma "estratégia" seria
questionar uma decisão informada que ela já tomou — o oposto do tom do
produto (mesmo raciocínio de nunca gerar recomendação de dose).
"""
from app.models.enums import MedicationSkipReason

REPEAT_THRESHOLD = 2

_TIPS: dict[MedicationSkipReason, str] = {
    MedicationSkipReason.ESQUECI: (
        "Isso já aconteceu mais de uma vez por esquecimento. Uma estratégia que "
        "costuma ajudar: prender a dose a um hábito que você já faz todo dia sem "
        "pensar (escovar os dentes, ligar a cafeteira) e deixar o remédio "
        "literalmente ao lado desse hábito, visível — em vez de confiar só na "
        "memória ou no lembrete sozinho."
    ),
    MedicationSkipReason.ROTINA_MUDOU: (
        "Sua rotina mudou mais de uma vez perto do horário desta dose. Pode valer "
        "religar o lembrete a um ponto fixo do seu dia (não a um horário do "
        "relógio) ou reagendar o horário da dose pra bater com o novo padrão."
    ),
    MedicationSkipReason.NAO_CONSEGUI_LEVANTAR: (
        "Se levantar tem sido o obstáculo mais de uma vez, deixar o remédio (e um "
        "copo d'água) ao alcance da cama, visível antes de qualquer outra coisa, "
        "tende a reduzir essa barreira mais do que um lembrete sonoro."
    ),
    MedicationSkipReason.EFEITO_ADVERSO: (
        "Efeito adverso se repetindo não é algo pra resolver sozinho(a) ajustando "
        "hábito — vale levar isso pra quem prescreveu, pra avaliar dose ou "
        "horário com acompanhamento médico."
    ),
    MedicationSkipReason.MEDO: (
        "Esse receio já apareceu mais de uma vez. Vale conversar com quem "
        "prescreveu sobre ele, sem pressa — decidir sozinho(a) parar ou ajustar a "
        "medicação pode não ser o caminho mais seguro."
    ),
    MedicationSkipReason.MEDICAMENTO_INDISPONIVEL: (
        "Se a indisponibilidade está se repetindo, vale verificar com a farmácia "
        "sobre estoque programado ou perguntar ao médico sobre uma receita de "
        "reserva."
    ),
    MedicationSkipReason.OUTRO: (
        "Esse mesmo motivo já apareceu mais de uma vez. Pode valer detalhar um "
        "pouco mais na próxima vez, ou conversar sobre isso com alguém da sua "
        "rede de confiança."
    ),
}


def tip_for_reason(reason: MedicationSkipReason) -> str | None:
    return _TIPS.get(reason)
