# Deploy em produção (ETAPA 35)

Este guia sobe o Gancho (backend + Postgres + frontend, com HTTPS
automático) em qualquer servidor Linux com Docker instalado — VPS
próprio ou uma máquina de um provedor gerenciado que aceite Docker
Compose. A escolha de ONDE rodar continua em aberto de propósito (ver
`docs/decisions.md`): estes arquivos não amarram o projeto a nenhum
provedor específico.

## Pré-requisitos no servidor

- Docker + Docker Compose v2 (`docker compose version`).
- Um domínio (ou subdomínio) com o DNS já apontando pro IP do
  servidor, em registros A/AAAA — o Caddy (proxy reverso) precisa
  disso pra emitir o certificado HTTPS automaticamente.
- Portas 80 e 443 livres e alcançáveis da internet.

## Passo a passo (primeira subida)

```bash
git clone <seu-repositório> gancho
cd gancho

cp backend/.env.production.example backend/.env.production
# edite backend/.env.production:
#   - JWT_SECRET_KEY: gere com
#       python3 -c "import secrets; print(secrets.token_urlsafe(64))"
#   - POSTGRES_PASSWORD: uma senha forte, diferente da de dev
#   - CORS_ORIGINS / FRONTEND_URL: seu domínio real, com https://
#   - SMTP_*: credenciais de um provedor SMTP real (sem isso, e-mail
#     de reset de senha continua só logado, nunca entregue)

export DOMAIN=seu-dominio.com
export VITE_API_BASE_URL=https://seu-dominio.com/api/v1

docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

A primeira emissão de certificado pelo Caddy pode levar alguns
segundos — acompanhe com `docker compose -f docker-compose.prod.yml
logs -f caddy` se `https://seu-dominio.com` não responder de
imediato.

Confirme que subiu:

```bash
curl https://seu-dominio.com/health   # ou abra no navegador
# {"status":"ok","environment":"production","database":"ok"}
```

Se a aplicação recusar subir com um erro de `JWT_SECRET_KEY` ou
`DEBUG` — isso é o guard de produção adicionado na ETAPA 30-32
funcionando como deveria: significa que `backend/.env.production`
ainda tem um valor de exemplo/inseguro. Corrija o arquivo, não o
código.

## Atualizando uma versão já no ar

```bash
git pull
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

`alembic upgrade head` é seguro de rodar mesmo sem migration nova —
não faz nada se o banco já está no estado mais recente.

## O que cada peça faz

- **`db`** — Postgres 16, dado persistido em volume nomeado (sobrevive
  a `docker compose down`, só é apagado com `docker compose down -v`).
  Porta 5432 NÃO é exposta pro host em produção (diferente do compose
  de dev) — só os outros serviços do compose alcançam o banco.
- **`api`** — a mesma imagem de `backend/Dockerfile`, agora rodando
  sem `--reload` e com `--workers` (padrão 2, ajustável via
  `WEB_CONCURRENCY` em `backend/.env.production`).
- **`frontend`** — build estático do React (Vite) servido por nginx;
  `VITE_API_BASE_URL` é gravado dentro do JS no momento do BUILD da
  imagem, não pode ser trocado só reiniciando o container — mudou o
  domínio, precisa rebuildar (`docker compose -f
  docker-compose.prod.yml build frontend`).
- **`caddy`** — único serviço exposto nas portas 80/443; emite e
  renova o certificado HTTPS sozinho (Let's Encrypt) e roteia
  `/api/*` pro backend, o resto pro frontend (ver `Caddyfile`).

## O que NÃO está incluído (decisão de escopo, não esquecimento)

- **Backup automático do Postgres**: fora do escopo desta etapa — o
  volume nomeado sobrevive a reinícios/updates, mas não substitui um
  backup de verdade (`pg_dump` agendado pra fora do servidor). Ver se
  o provedor escolhido já oferece isso antes de implementar um.
- **Monitoramento/alertas de infraestrutura** (uptime, uso de
  CPU/memória/disco): idem — muitos provedores já oferecem isso de
  fábrica; avaliar antes de adicionar ferramenta nova.
- **CI de deploy automático** (a cada push em `main`, subir sozinho em
  produção): o CI existente (`.github/workflows/ci.yml`) só RODA OS
  TESTES; conectar isso a um deploy automático depende de qual
  servidor/provedor for escolhido, então fica pra quando essa escolha
  for feita.
