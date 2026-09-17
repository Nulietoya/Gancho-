"""
Camada psicoeducativa. Pedido do usuário: dar respaldo científico e
analítico do por quê os desvios costumam ocorrer — tanto pro próprio
dono da conta quanto pra pessoa de confiança, que "nem sempre entende
essas mudanças e variações" (o padrão mental disponível pra ela, sem
isso, costuma ser "ele não fez o que prometeu de novo" lido como falta
de caráter, não como um mecanismo real).

Regra igual à de todo o resto do produto (docs/architecture.md, seção
6, mesmo princípio de `enums.py`/`alert_service`): isto NUNCA é
diagnóstico e nunca aponta um mecanismo específico como "a causa" da
mudança DESTA pessoa — é o mecanismo geral, com respaldo na literatura
sobre TDAH/procrastinação, que costuma estar por trás desse tipo de
padrão. Texto fixo por motor (não gerado, não personalizado a nenhum
dado do usuário) — pluga no `EngineExplanation`/`TrustedAlertExplanation`
já existentes sem recalcular nada, mesmo raciocínio já registrado em
`explainability_service` ("nunca recalcula, só organiza").

Duas versões por motor porque o público muda o que precisa ouvir: a
versão do dono ajuda a pessoa a entender o que está sentindo sem se
julgar; a versão da pessoa de confiança troca "por que isso acontece"
por "o que fazer a respeito" (nunca uma instrução clínica — só o tipo
de postura que a própria literatura de acompanhamento de TDAH associa
a resultado melhor: presença sem cobrança, redução do tamanho da
tarefa, pergunta em vez de pressão).
"""
from app.models.enums import DeviationEngine

OWNER_CONTEXT: dict[DeviationEngine, str] = {
    DeviationEngine.EXECUTIVE: (
        "Começar, planejar e terminar tarefas depende de funções executivas — "
        "processos cerebrais que variam de um dia pro outro, e variam mais em "
        "quem tem TDAH. Uma queda sustentada aqui costuma ser flutuação real "
        "de função executiva, não falta de esforço ou de força de vontade — é "
        "um padrão que aparece de forma consistente na pesquisa sobre TDAH, "
        "não um traço de caráter."
    ),
    DeviationEngine.AVOIDANCE: (
        "Ansiedade e evitação costumam se alimentar uma da outra: evitar uma "
        "tarefa alivia a ansiedade por um instante, o que ensina o cérebro a "
        "evitar de novo na próxima vez — um ciclo bem documentado, não uma "
        "escolha deliberada. Quanto mais esse ciclo se repete, maior a tarefa "
        "evitada costuma parecer."
    ),
    DeviationEngine.ACTIVATION: (
        "Uma queda de energia sustentada pode refletir dificuldade real de "
        "ativação — o esforço extra que o cérebro com TDAH costuma precisar "
        "pra sair da inércia e começar a se mover, mesmo diante de algo "
        "importante. Está ligada à forma como o TDAH afeta a regulação de "
        "dopamina, não a desmotivação ou preguiça."
    ),
    DeviationEngine.STABILITY: (
        "Sono, humor e adesão à medicação se afetam mutuamente: dormir mal "
        "tende a piorar sintomas de TDAH no dia seguinte, e sintomas piores "
        "dificultam manter a rotina de sono e de medicação — fechando um "
        "ciclo. Uma queda aqui costuma ser esse ciclo se manifestando, não um "
        "sinal isolado de cada peça; e quando a adesão à medicação cai, na "
        "maioria das vezes é esquecimento ou efeito colateral, não decisão de "
        "abandonar o tratamento."
    ),
}

TRUSTED_PERSON_CONTEXT: dict[DeviationEngine, str] = {
    DeviationEngine.EXECUTIVE: (
        "Isso geralmente não é preguiça nem falta de compromisso: começar e "
        "terminar tarefas depende de função executiva, que oscila de verdade "
        "em quem tem TDAH. Cobrar ou pressionar tende a piorar — presença sem "
        "julgamento (como acompanhar a tarefa junto, sem cobrar o resultado) "
        "costuma ajudar mais do que insistência."
    ),
    DeviationEngine.AVOIDANCE: (
        "Isso costuma ser um ciclo de ansiedade e evitação, não desinteresse: "
        "evitar alivia a ansiedade por um momento, o que reforça evitar de "
        "novo. Insistir pra 'só fazer logo' tende a aumentar a ansiedade que "
        "está causando a evitação — ajuda mais reduzir o tamanho da tarefa "
        "junto com a pessoa do que pressionar pelo resultado."
    ),
    DeviationEngine.ACTIVATION: (
        "Uma queda de energia sustentada não costuma ser falta de vontade — é "
        "um estado real de dificuldade em começar a se mover, ligado à forma "
        "como o TDAH afeta a regulação de dopamina. Reduzir a exigência (um "
        "passo pequeno, não a tarefa inteira) tende a funcionar melhor do que "
        "pedir mais esforço."
    ),
    DeviationEngine.STABILITY: (
        "Sono, humor e adesão à medicação se afetam mutuamente — quando um "
        "piora, os outros costumam seguir. Se a adesão à medicação caiu, na "
        "maioria dos casos é esquecimento ou efeito colateral, não decisão de "
        "parar o tratamento — vale perguntar com curiosidade, não cobrança."
    ),
}


def owner_scientific_context(engine: DeviationEngine) -> str:
    return OWNER_CONTEXT[engine]


def trusted_person_scientific_context(engine: DeviationEngine) -> str:
    return TRUSTED_PERSON_CONTEXT[engine]
