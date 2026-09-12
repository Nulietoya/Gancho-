# Gancho

Sistema de apoio a padrões de funcionamento pessoal (nome de trabalho:
"Gancho" — o mesmo usado nas automações e no painel já existentes do
projeto). Não é uma ferramenta de diagnóstico: identifica mudanças no
funcionamento habitual de uma pessoa (procrastinação, evitação,
isolamento, quebra de rotina, adesão a medicação) e permite que uma
rede de confiança autorizada seja notificada segundo regras definidas
pelo próprio usuário enquanto está estável.

Ver `docs/architecture.md` para a arquitetura completa e
`docs/decisions.md` para o histórico de decisões técnicas e por quê
foram tomadas.

## Rodando localmente

### Opção 1 — Docker Compose (recomendado)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

API sobe em `http://localhost:8000`, Postgres em `localhost:5432`.

### Opção 2 — sem Docker

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ajuste DATABASE_URL se necessário
uvicorn app.main:app --reload
```

Verifique se subiu:

```bash
curl http://localhost:8000/health
# {"status":"ok","environment":"development","database":"ok"}
```

## Testes

```bash
cd backend && source .venv/bin/activate
pytest -q
```

## Migrations (Alembic)

```bash
cd backend && source .venv/bin/activate
alembic revision --autogenerate -m "descrição da mudança"
alembic upgrade head
```

## Estado atual

MVP completo — as 36 etapas do roteiro de referência (ver
`docs/decisions.md`) estão concluídas. Etapas: **ETAPA 1-4, 6-14 e
16-26**
(requisitos, arquitetura/stack, estrutura do projeto, modelo de
dados completo, autenticação completa, autorização + pessoas de
confiança + observações externas, perfil/onboarding guiado, tarefas
com máquina de estados orientada a eventos, check-ins diários,
rotina de referência + eventos de vida, medicamentos/adesão, motor
de baseline, motor de desvio com os 4 motores
Executivo/Evitação/Ativação/Estabilidade, modelo de estado
verde/amarelo/vermelho, explicabilidade navegável por indicador,
intervenções — microintervenção com catálogo rotativo e body
doubling ponta a ponta —, notificações — motor de anti-spam (horário
silencioso + teto diário, nunca contendo estado VERMELHO), e-mail de
verdade para reset de senha, e ciclo noturno automático via
APScheduler que sincroniza baseline/desvio/alerta e preenche doses de
medicação esquecidas sem depender de a pessoa lembrar de abrir o
app —, e dashboards: painel diário (estado atual, check-in de hoje,
doses do dia, intervenções em andamento, notificações não lidas),
painel analítico (linha do tempo de estado, tendência por indicador,
histórico de desvio, adesão a medicação, estatística de
intervenções) e o painel restrito da pessoa de confiança, onde cada
seção só aparece se a permissão concedida autorizar — nunca "vê tudo
porque está autenticada"), e configurações/privacidade: plano pessoal
estilo WRAP ("plano quando eu não perceber", item 19) editável pelo
dono e visível à pessoa de confiança só com `ACCESS_CRISIS_PLAN`
concedida, exportação de dados em JSON e exclusão de conta (soft
delete, com reconfirmação de senha e revogação de toda sessão) —
LGPD: minimização, consentimento, exportação, exclusão, auditoria; e
auditoria: as três lacunas que ficaram como enum "pré-modelado, sem
uso" desde o início — login, troca de senha e transição pra estado
crítico — agora gravam de verdade, mais `GET /audit-log` pra pessoa
consultar (paginado) o que aconteceu com a própria conta.
207 testes automatizados de backend passando (um bug real de
indicador obsoleto corrigido numa revisão geral pós-ETAPA 20, um bug
de infraestrutura de teste — não de produto — corrigido na ETAPA 22,
e um bug real de idempotência em `deactivate_plan` corrigido na
ETAPA 25, ver `docs/decisions.md`).

**ETAPA 27 (frontend) — concluída, entregue em 8 levas**: React +
TypeScript + Vite em `frontend/`, conectado de verdade ao backend.
Cobre autenticação, painel diário e check-in; tarefas (criar e
avançar pela máquina de estados — iniciar/pausar/adiar/concluir/
cancelar); rede de confiança (convidar, permissões granulares,
revogar, observações) e o painel operacional de quem RECEBE confiança
(`/observando` — dashboard restrito por permissão, registrar
observação, sugerir tarefa, aceitar pedido de acompanhamento);
medicação e rotina de referência; alertas com explicação navegável e
painel analítico; plano pessoal ("plano quando eu não perceber") e
configurações de conta (trocar senha, exportar dados, desativar
conta); e visualizador de auditoria. Relato leva a leva completo em
`docs/decisions.md`. Tudo verificado ponta a ponta com Playwright em
contas reais (não só `npm run build`).

**ETAPA 28 — concluída**: estados de loading/erro/vazio (já cobertos
desde a 1ª leva) mais os dois gaps reais fechados — mensagem de erro
sensível a rede caída/servidor fora do ar (`describeError`, em vez do
"Failed to fetch" cru) e um `ErrorBoundary` global (tela de
recuperação em vez de branco, em qualquer erro de render inesperado),
com aviso de offline persistente no cabeçalho.

**ETAPA 29 — concluída**: suíte de testes automatizados de frontend,
commitada — Vitest + React Testing Library (25 testes unit/componente,
`npm test`) e Playwright (6 specs E2E ponta a ponta contra
backend+frontend reais, `npm run test:e2e`, sobe os dois servidores
sozinho). Formaliza os scripts ad hoc usados pra verificar cada leva
da ETAPA 27 em algo que continua rodando depois da sessão.

**ETAPA 30-32 — concluída**: revisão de segurança, banco de
dados/performance e UX/acessibilidade. Segurança: reuso de refresh
token já rotacionado agora é detectado como possível roubo de sessão
e revoga toda sessão ativa do usuário (com auditoria própria);
cabeçalhos de segurança de resposta (`X-Content-Type-Options`,
`X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`,
`Strict-Transport-Security` em produção); e a aplicação agora recusa
subir com `ENVIRONMENT=production` e o segredo de JWT ou `debug`
ainda no valor de fábrica, em vez de só avisar em comentário. Banco:
2 índices reais faltando corrigidos
(`Observation.relationship_id`, `Intervention.support_relationship_id`).
UX/acessibilidade e rate limit por IP: revisados, ver
`docs/decisions.md` pelo raciocínio de cada decisão de manter como
está.

**ETAPA 33-34 — concluída**: `pytest-cov` instalado pra medir
cobertura de verdade (95%→97%), e as lacunas reais que a métrica
apontou foram fechadas — nunca perseguindo 100% por perseguir.
Removida uma função morta (`get_checkin_by_id`, nunca chamada por
nada). 8 testes novos cobrindo comportamento de produto nunca
exercitado: 404 de posse em toda rota mutante de tarefas e
medicamentos (não só a primeira), `ScheduleNotFound` quando o
horário pertence a outro medicamento, caminho de sucesso de
`update_schedule`/`list_schedules`/`list_events_for_schedule`,
filtro por período do histórico de check-in, e os dois ramos que
faltavam (`not_helped`/`no_result`) da estatística de intervenção do
painel analítico. Ver `docs/decisions.md` para o raciocínio completo.

**ETAPA 35 — concluída**: ambiente de produção. Rate limit por IP nas
rotas sensíveis de autenticação (`slowapi`, em memória — só ativo com
`ENVIRONMENT=production`, decisão revisitada da ETAPA 30-32: não
precisava de Redis pra uma implantação de instância única). CI
(GitHub Actions, `.github/workflows/ci.yml`) rodando backend e
frontend a cada push/PR — decisão adiada da ETAPA 29. Imagem de
produção do backend (sem `--reload`, workers configuráveis, usuário
não-root) e do frontend (build estático + nginx, multi-stage) mais
`docker-compose.prod.yml` com Caddy fazendo HTTPS automático — ver
`docs/deploy.md` pro passo a passo. Dois achados reais corrigidos
antes de considerar pronto: `.dockerignore` ausente em ambos os
serviços (`COPY . .` copiaria o `.env` local com segredos de verdade
pra dentro da imagem do backend, e o `node_modules` do host por cima
do que o `npm ci` acabou de instalar no do frontend) e a forma
"shell" do `CMD` do backend (não repassa `SIGTERM` de forma
confiável — trocada pela forma `exec` recomendada).

**ETAPA 36 — concluída**: documentação final. Não é feature nova —
auditoria de `docs/architecture.md` (o documento mais antigo do
projeto, escrito antes de qualquer código, nunca revisado desde
então) contra o que o sistema de fato faz hoje. 5 divergências reais
corrigidas: diagrama mostrava um "Worker" separado pro APScheduler
(na verdade roda embutido no processo da própria API desde a ETAPA
22); "Web Push" e "PWA" apareciam como já implementados (nunca
foram — só in-app + e-mail via SMTP, e SPA sem manifest/service
worker); "deploy em aberto" (verdade até a ETAPA 35, hoje os
artefatos existem); e a mais importante — o documento afirmava
"criptografia em repouso" como requisito cumprido, quando nenhuma
peça do projeto implementa isso (checado por grep antes de corrigir)
— um documento de arquitetura de um app de dado de saúde/comportamento
não deveria prometer uma garantia de segurança que o código não
entrega. Ver `docs/decisions.md` para as 5 divergências completas.
Com esta etapa, as 36 etapas do roteiro de referência estão
concluídas.

## Rodando o frontend

```bash
cd frontend
npm install
cp .env.example .env   # aponta pra http://localhost:8000/api/v1 por padrão
npm run dev
```

Abre em `http://localhost:5173` — precisa do backend rodando (ver
acima) e do `CORS_ORIGINS` do backend incluindo essa origem (já vem
assim por padrão em `backend/.env.example`).

## Produção

`docker-compose.prod.yml` + `docs/deploy.md` — sobe backend, Postgres,
frontend (build estático servido por nginx) e um proxy Caddy na
frente cuidando de HTTPS automático, em qualquer servidor com Docker.
Passo a passo completo, incluindo variáveis de ambiente necessárias,
em `docs/deploy.md`.

## CI

`.github/workflows/ci.yml` roda `pytest --cov` (backend, contra um
Postgres efêmero) e `npm run lint && npm run build && npm test`
(frontend) a cada push/PR pra `main`. E2E (Playwright) fica de fora do
CI por decisão de escopo — ver comentário no próprio workflow.

## Testes do frontend

```bash
cd frontend
npm test           # unit/componente (Vitest + Testing Library) — rápido, sem servidor
npm run test:e2e   # ponta a ponta (Playwright) — sobe backend+frontend sozinho,
                    # só precisa do Postgres já rodando e do backend/.venv já criado
```

`npm run test:e2e` baixa o Chromium do Playwright na primeira vez
(`npx playwright install chromium`) se ele ainda não estiver
instalado. Em ambientes com um Chromium fixo pré-instalado noutro
caminho (sem acesso pra baixar), aponte pra ele via
`PLAYWRIGHT_CHROMIUM_PATH=/caminho/pro/chrome npm run test:e2e`.
