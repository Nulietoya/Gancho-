# Arquitetura — Gancho

## 1. O que o sistema é (e não é)

Identifica **mudanças no funcionamento habitual** de uma pessoa
(procrastinação, evitação, isolamento, quebra de rotina, sono,
adesão a medicação) comparando o estado atual com o **baseline
individual** dela — nunca com uma média populacional. Não
diagnostica TDAH, ansiedade, depressão ou qualquer transtorno. Nunca
decide sozinho sobre crise; no máximo orienta buscar ajuda humana e
segue regras de contato previamente autorizadas pelo próprio usuário
enquanto estável (estilo WRAP).

O mesmo sistema serve as duas trilhas do projeto: **Trilha A** (uso
pessoal do usuário original) é apenas "usuário nº 1" dentro deste
modelo — nenhuma entidade especial é necessária para ela. **Trilha
B** (outras pessoas com a mesma dificuldade, ex. persona "Marina")
usa exatamente a mesma base, com seus próprios dados e sua própria
rede de confiança.

## 2. Módulos

| Módulo | Responsabilidade |
|---|---|
| Auth | cadastro, login, sessão, recuperação de senha |
| Users/Profile | dados do usuário, onboarding, plano pessoal de deterioração |
| Trusted People & Permissions | convite de pessoas de confiança, permissões granulares por pessoa |
| Check-in diário | captura curta e de baixo esforço do estado do dia |
| Tasks | tarefas com estado, adiamentos, motivo de não realização |
| Routines | rotina habitual declarada (sono, saída de casa, trabalho/estudo) |
| Medications | medicação prescrita, adesão (não prescrição nem dosagem) |
| Observations | registro de observação externa por pessoa de confiança |
| Baseline Engine | calcula padrão individual por variável, com janela configurável |
| Deviation Engine | compara estado atual x baseline, por "motor" (Executivo, Evitação, Ativação, Estabilidade) |
| Alerts / States | Verde / Amarelo / Vermelho, sempre com explicação |
| Interventions | microintervenções sugeridas, body doubling |
| Notifications | lembretes, alertas, pedidos de apoio — com preferências e limites |
| Audit Log | toda ação sensível (login, permissão, acesso a dado restrito) |
| Analytics Dashboard | evolução semanal/mensal, motivos de adiamento, correlações |
| Personal Plan | plano pessoal estilo WRAP ("plano quando eu não perceber"), visível à pessoa de confiança só com permissão própria |
| Account/Privacy | exportação de dados (JSON) e exclusão de conta (soft delete), LGPD |

## 3. Arquitetura técnica

```
┌─────────────┐        HTTPS/JSON        ┌───────────────────────────┐
│  Frontend    │ ───────────────────────▶ │   API (FastAPI)           │
│  React + TS  │ ◀─────────────────────── │   /api/v1/*               │
│  (SPA)       │                          │                           │
└─────────────┘                          │  BackgroundScheduler      │
                                          │  (APScheduler, embutido   │
                                          │  no mesmo processo via    │
                                          │  lifespan — não é um      │
                                          │  serviço/deploy separado) │
                                          │  - ciclo noturno 3h UTC:  │
                                          │    baseline/desvio/alerta,│
                                          │    dose esquecida         │
                                          │  - entrega de notificação │
                                          │    represada, a cada 15min│
                                          └──────────┬────────────────┘
                                                     │ SQLAlchemy
                                          ┌──────────▼────────────────┐
                                          │  PostgreSQL                │
                                          └─────────────────────────────┘
```

- **Backend monolítico modular** (não microserviços). Um único
  deploy, módulos separados por domínio dentro do código
  (`app/api/v1/<dominio>.py`, `app/services/<dominio>.py`). Justifica
  a decisão em "5. Escalabilidade" abaixo.
- **Autorização em duas camadas**: autenticação (JWT) diz "quem é";
  uma camada de autorização própria (tabela `permissions`, verificada
  no backend em cada endpoint sensível) diz "o que pode ver/fazer".
  Nunca confiar em esconder botão no frontend.
- **Motor analítico plugável**: baseline e desvio são serviços com
  interface fixa (`compute_baseline(user_id, variable)`,
  `compute_deviation(user_id)`), para permitir trocar o método
  (regra simples → estatística → ML) sem reescrever o resto do
  produto (exigência do documento de referência, item 38).
- **Jobs agendados no próprio processo da API, não num worker
  separado**: `BackgroundScheduler` do APScheduler é ligado no
  `lifespan` do FastAPI (`app/core/scheduler.py`) — não existe um
  segundo serviço/container pra rodar (`docker-compose.yml`/
  `docker-compose.prod.yml` só sobem `api`, sem um `worker`). Correto
  pro volume esperado do MVP; viraria um worker de verdade só se um
  dia o job ficar pesado o bastante pra competir por CPU com as
  requisições HTTP no mesmo processo — não é o caso hoje.

## 4. Stack escolhida e por quê

| Camada | Escolha | Por quê |
|---|---|---|
| Backend | Python + FastAPI | tipagem forte com Pydantic (contratos de API auto-documentados em `/docs`), assíncrono quando precisar, e principalmente: os motores de baseline/desvio são estatística sobre séries temporais — Python tem o ecossistema (pandas/numpy/scipy) que vai ser usado a partir da Fase 2 sem trocar de linguagem |
| Banco | PostgreSQL | relacional (o domínio é fortemente relacional: usuário → tarefas → eventos → observações), suporta JSON quando um campo precisa ser flexível (payload de indicador), maduro, fácil de rodar em qualquer provedor depois |
| ORM/Migrations | SQLAlchemy + Alembic | migrations versionadas e revisáveis — obrigatório para um sistema que guarda dado de saúde/comportamento e precisa de histórico auditável de schema |
| Auth | JWT próprio (access + refresh), senha com Argon2 | o modelo de permissão exigido (granular, por pessoa, revogável, testado no backend) é específico do domínio — nenhum provedor de auth genérico (Auth0/Firebase Auth) cobre "pessoa de confiança vê X mas não Y" sem reimplementar por cima de qualquer forma. Rodar auth própria evita pagar a complexidade de um provedor externo para depois recriar a mesma lógica |
| Frontend | React + TypeScript + Vite (SPA) | cobre celular/tablet/desktop com uma base de código só (responsivo), sem precisar de app nativo na v1; PWA (instalar na tela inicial, Web Push nativo) fica pra Fase 2 — não implementado ainda, decisão de escopo, não esquecimento |
| Notificações (MVP) | in-app + e-mail via SMTP (fallback: backend de log se SMTP não configurado) | cobre os dois pontos de disparo reais (alerta e pedido de apoio) sem depender de infraestrutura de push própria; Web Push fica pra quando existir PWA/app nativo — não era necessário para provar a hipótese do produto |
| Jobs agendados | APScheduler embutido no processo da própria API (não um worker separado) | um cron simples resolve o volume esperado no MVP (poucos milhares de usuários no máximo); fila com Redis/Celery só se isso deixar de ser verdade — ver "Evite overengineering" no documento de referência |
| Rate limit por IP | `slowapi`, em memória, ativo só em produção | complementa (não substitui) o bloqueio por conta já existente desde a ETAPA 6; migra pra Redis via `storage_uri`, sem tocar em rota, se um dia rodar múltiplas instâncias — ver `docs/decisions.md`, ETAPA 35 |
| Infra local/dev | Docker Compose (api + Postgres, hot-reload) | um comando sobe o ambiente inteiro, igual em qualquer máquina |
| Infra produção | Docker Compose (api + Postgres + frontend/nginx + Caddy) | mesmas imagens do dev, `command`/config diferentes; Caddy cuida de HTTPS automático (Let's Encrypt) sem configurar certbot na mão — passo a passo em `docs/deploy.md` |
| Hospedagem (servidor) | Em aberto, de propósito | decisão de custo/operação do usuário, não técnica — os artefatos de produção rodam em qualquer servidor com Docker (VPS, Railway, Fly.io, Render, etc.), sem mudança de código |
| CI | GitHub Actions (`.github/workflows/ci.yml`) | backend (Postgres efêmero + `pytest --cov`) e frontend (lint+build+test) a cada push/PR; E2E (Playwright) roda manualmente antes de um release — decisão de escopo (dobraria o tempo de cada rodada de CI) |

## 5. Escalabilidade sem overengineering

Nada aqui foi desenhado para "escala do Google". Foi desenhado para
não precisar ser reescrito quando sair de 1 usuário (Trilha A) para
algumas centenas (Trilha B em validação):

- Monolito modular hoje → cada módulo já isolado o suficiente para
  virar serviço próprio depois, **se** algum dia isso for necessário.
- Índices e paginação desde a ETAPA 4 (não depois).
- Baseline/desvio calculados em batch (job noturno + no momento do
  check-in), não em tempo real por sensor — o domínio é diário, não
  contínuo, então não precisa de stream processing.

## 6. Segurança e privacidade (aplicado desde a ETAPA 4)

- Dado de saúde/comportamento é dado sensível (LGPD, art. 5º, II) —
  minimização de dados, controle de acesso, log de auditoria,
  exportação e exclusão pelo titular são requisitos de v1, aplicados
  desde a ETAPA 4 (modelo de dados) e completados nas ETAPA 25/26.
  Criptografia em trânsito é real desde a ETAPA 35 (HTTPS automático
  via Caddy em produção). Criptografia EM REPOUSO do banco (disco)
  não é implementada por nenhuma peça deste projeto — depende de o
  servidor/provedor de banco escolhido oferecer disco criptografado
  (a maioria dos provedores gerenciados de Postgres oferece por
  padrão); registrado aqui de propósito pra não sugerir uma garantia
  que o código não entrega sozinho.
- Nenhuma pessoa de confiança acessa dado não autorizado nem
  manipulando endpoint diretamente — autorização é sempre verificada
  no backend, nunca só escondendo botão no frontend (testado
  explicitamente em toda rota restrita; ver ETAPA 7/14/16 e a
  varredura de autorização da ETAPA 33-34 em `docs/decisions.md`).
- Reuso de refresh token já rotacionado é tratado como possível roubo
  de sessão: revoga toda sessão ativa do usuário, nunca só nega o
  pedido isolado (ETAPA 30-32).
- Cabeçalhos de segurança de resposta HTTP (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`,
  `Strict-Transport-Security` em produção) e rate limit por IP nas
  rotas de autenticação (ETAPA 30-32/35).
- A aplicação recusa subir com `ENVIRONMENT=production` se o segredo
  de JWT ou `debug` ainda estiverem no valor de fábrica (ETAPA 30-32).
- IA (quando entrar, Fase 3) é camada auxiliar: nunca diagnostica,
  nunca prescreve, nunca decide sozinha sobre crise, nunca aciona
  terceiro sem regra previamente autorizada.

## 7. Fases

- **MVP (Fase 1) — concluído**: autenticação, onboarding, check-in,
  tarefas, rotina, pessoa de confiança, permissões granulares,
  observação externa, baseline, motor de desvio (4 motores), estados
  Verde/Amarelo/Vermelho com explicabilidade, intervenções
  (microintervenção + body doubling), notificações com anti-spam,
  dashboards (dono + pessoa de confiança), plano pessoal, privacidade/
  LGPD (exportação + exclusão), auditoria — backend e frontend
  completos e testados (225 testes de backend, 25 unit/componente +
  6 E2E de frontend), mais ambiente de produção (rate limit, CI,
  Docker, HTTPS automático). Lista etapa a etapa completa em
  `decisions.md` e no doc do projeto.
- **Fase 2 (não iniciada)**: baseline adaptativo, motor de desvio por
  domínio refinado, experimentos pessoais (N=1), correlações,
  relatórios, verificação de e-mail no cadastro, canal de entrega de
  convite (hoje o link só existe no banco), PWA (instalar na tela
  inicial) + Web Push nativo.
- **Fase 3 (não iniciada)**: IA auxiliar (resumir padrões, classificar
  texto livre, sugerir divisão de tarefa), análise longitudinal mais
  sofisticada, papel profissional (psicólogo/médico) — nunca antes
  disso.
