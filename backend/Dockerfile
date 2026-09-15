FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ETAPA 35: imagem passou a ser a de PRODUÇÃO por padrão — sem
# `--reload` (que também deixa o processo mais lento e não deveria
# rodar num servidor de verdade) e sem rodar como root. O
# `docker-compose.yml` de desenvolvimento sobrescreve `command:` com
# `--reload` por cima desta mesma imagem, então não existe um
# segundo Dockerfile pra manter sincronizado.
RUN useradd --create-home --uid 1000 gancho
USER gancho

EXPOSE 8000

# Um worker por padrão: o lifespan da API inicia o APScheduler dentro
# do processo. Múltiplos workers executariam os mesmos jobs em paralelo.
# Para escalar a API, separe primeiro o scheduler em um processo único
# e use armazenamento compartilhado para o rate limit.
#
# CMD em forma de lista com `sh -c 'exec ...'` (não a forma "shell"
# simples `CMD uvicorn ...`) de propósito: o linter do próprio
# `docker build` aponta a forma simples como arriscada porque o
# uvicorn rodaria como filho do `/bin/sh`, que não repassa SIGTERM
# de forma confiável — um `docker stop`/redeploy então esperaria o
# timeout inteiro e mataria à força em vez de encerrar graciosamente
# as conexões em andamento. O `exec` troca o processo do shell pelo
# do uvicorn (mesmo PID), que passa a receber o sinal direto.
ENV WEB_CONCURRENCY=1
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY}"]
