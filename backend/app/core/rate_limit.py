"""
Rate limit por IP (ETAPA 35).

Registrado como lacuna desde a ETAPA 6 ("a camada que falta quando o
volume justificar") e revisitado explicitamente na ETAPA 30-32, que
decidiu adiar pra esta etapa por parecer, à primeira vista, exigir
infraestrutura compartilhada entre processos (Redis) — mesmo padrão
de cautela já registrado contra Celery/Redis neste projeto.

Na prática, `slowapi` (wrapper fino sobre `limits`) guarda o contador
em memória do próprio processo por padrão — suficiente para o deploy atual, que força um único worker de API.
Antes de adicionar workers ou réplicas, configure armazenamento
compartilhado (`storage_uri`) para os contadores e mova o scheduler
para um processo único.

Só ativo em produção, de propósito: em dev/test o limite não protege
nada real (localhost não é superfície de ataque de verdade) e só
atrapalharia — a própria suíte de testes faz muito mais que N
requisições por minuto na mesma rota, de propósito, pra testar outros
comportamentos.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.environment == "production",
)
