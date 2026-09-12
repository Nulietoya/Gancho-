"""
Um único `utc_now()` pro projeto inteiro. Encontrado numa revisão
geral: o mesmo `def _now(): return datetime.now(timezone.utc)`
estava duplicado, palavra por palavra, em 6 services diferentes
(`task_service`, `checkin_service` só que inline, `routine_service`,
`medication_service`, `baseline_service`, `deviation_service`,
`alert_service`) — nenhum bug (todos faziam a mesma coisa certa),
mas repetição sem motivo. Cada service continua expondo seu próprio
`_now()` local (só que agora um alias deste), pra não precisar tocar
em nenhuma chamada existente.
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
