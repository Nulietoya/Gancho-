# Decisões — histórico

Este arquivo é o registro de decisões técnicas e de produto tomadas
durante a construção, na ordem em que foram tomadas. Cada entrada
nova vai no topo.

---

## 2026-09-12 — ETAPA 36: documentação final

### Escopo desta etapa

Última etapa do roteiro de 36. Não é feature nova — é auditoria da
própria documentação (`docs/architecture.md`, `docs/decisions.md`,
`docs/deploy.md`, `README.md`, doc do projeto) contra o que o código
de fato faz hoje, depois de 35 etapas de mudança acumulada. O
documento mais antigo do projeto (`docs/architecture.md`, escrito na
ETAPA 2-3, antes de qualquer linha de código) nunca tinha sido
revisado — era o candidato óbvio a ter ficado pra trás.

### Achados reais (documentação desalinhada do código, não bug de produto)

Comparado `docs/architecture.md` contra o código de verdade e achadas
5 divergências reais, todas na direção "o documento promete/descreve
algo que o código não faz (mais), ou faz diferente":

1. **Diagrama mostrava um "Worker (APScheduler)" como processo
   separado.** Falso desde que foi escrito: o `BackgroundScheduler` é
   ligado no `lifespan` do próprio FastAPI (`app/core/scheduler.py`,
   ETAPA 22) — roda no MESMO processo da API. Nem
   `docker-compose.yml` nem `docker-compose.prod.yml` jamais tiveram
   um serviço `worker`. Um engenheiro novo lendo o diagrama antigo
   erraria a topologia de deploy achando que falta subir um segundo
   serviço.
2. **"Notificações (MVP): Web Push + e-mail (fallback)"** — nunca foi
   implementado Web Push; o motor de notificação (ETAPA 22) é in-app
   (tabela `Notification`) + e-mail via SMTP. Corrigido, e Web Push
   movido explicitamente pra lista da Fase 2 (não removido do
   documento, só corrigido de posição).
3. **"Deploy (produção): Em aberto"** — verdade quando escrito
   (ETAPA 2-3), falso desde a ETAPA 35: os artefatos de produção
   existem (Docker + Caddy). Corrigido, mantendo em aberto só a
   escolha do SERVIDOR/provedor de hospedagem em si — essa parte
   continua sendo decisão de custo do usuário, não técnica.
4. **"PWA" citado duas vezes no documento de stack** (frontend e
   notificações) como se já existisse — nunca foi implementado
   (confirmado: nenhum `manifest.json`/service worker no frontend).
   Corrigido pra "SPA" e a menção de PWA movida pra Fase 2.
5. **"criptografia em repouso e trânsito" listada como requisito
   cumprido de v1.** Trânsito é real desde a ETAPA 35 (HTTPS via
   Caddy). Em repouso (disco do Postgres) NUNCA foi implementado por
   nenhuma peça deste projeto — checado (`grep` por `pgcrypto`/
   `encrypt` em `app/`, zero ocorrência) antes de escrever esta
   entrada. Esta é a divergência mais importante das 5: um documento
   de arquitetura de um app que lida com dado de saúde/comportamento
   afirmando uma garantia de segurança que o código não entrega
   seria, na prática, uma informação enganosa pra quem decidir
   hospedar isso — corrigido pra deixar explícito que depende do
   provedor de banco escolhido oferecer disco criptografado (a
   maioria dos gerenciados oferece por padrão, mas não é algo que
   este código configura sozinho).

Também adicionados ao documento (nunca estavam lá, não por terem
mudado, mas por terem sido esquecidos ao escrever a versão original):
os módulos `Personal Plan` (ETAPA 25) e `Account/Privacy` (ETAPA 25)
na tabela de módulos; rate limit por IP e CI na tabela de stack;
seção de segurança atualizada com os 3 achados reais da ETAPA 30-32.
Seção "Fases" marcada com o que de fato está concluído (Fase 1/MVP
inteira) vs. não iniciado (Fase 2/3), em vez de ler como um plano
futuro genérico.

### Por que não foi tratado como "bug" formal

Nenhuma destas 5 divergências afeta o comportamento do sistema em
produção — são só o texto do documento desatualizado em relação ao
código que o próprio processo desta sessão já corrigiu ao longo das
etapas anteriores. Registradas aqui como decisão de escopo da ETAPA
36 (auditoria de documentação), não como "bug corrigido" nas etapas
onde a divergência começou a existir — o comportamento nunca esteve
errado, só o relato dele.

### Verificação

Releitura de `docs/architecture.md` do início ao fim depois da
edição, cruzando cada afirmação técnica restante contra o código
(`app/core/scheduler.py`, `app/core/rate_limit.py`, `docker-compose*.yml`,
`Caddyfile`, ausência de manifest PWA no frontend, grep por
criptografia). `README.md`, `docs/decisions.md` e `docs/deploy.md` já
estavam alinhados ao código real (escritos/atualizados a cada etapa
fechada nesta mesma sessão, não de uma vez no fim) — conferidos, sem
divergência encontrada. Suíte de backend não alterada nesta etapa (225
testes, nenhuma mudança de código de produto) — só documentação.

Com esta etapa, as 36 etapas do roteiro estão concluídas.

---

## 2026-09-12 — ETAPA 35: ambiente de produção

### Escopo desta etapa

Três peças que ficaram registradas como adiadas em etapas anteriores,
todas fechadas aqui: rate limit por IP (adiado da ETAPA 30-32), CI
(adiado da ETAPA 29), e os artefatos de deploy em si (Dockerfiles de
produção, compose de produção, runbook) — a peça que faltava pra
"ambiente de produção" deixar de ser só um docker-compose de
desenvolvimento. Hospedagem continua **em aberto** de propósito (não
é decisão técnica, é decisão de custo/operação do usuário): os
artefatos aqui rodam em qualquer servidor com Docker, sem prender o
projeto a nenhum provedor específico.

### Rate limit por IP — decisão revisitada

A ETAPA 30-32 tinha adiado isso citando a necessidade de "estado
compartilhado entre processos (Redis)" pra funcionar de verdade.
Reexaminado aqui: `slowapi` (wrapper fino sobre a lib `limits`) guarda
o contador em memória do próprio processo por padrão — suficiente pra
uma implantação de uma instância só, que é o que este MVP tem hoje —
e migra pra Redis só trocando `storage_uri` na construção do
`Limiter`, sem tocar em nenhuma rota, no dia em que precisar rodar
mais de um worker atrás de um load balancer. Ou seja: a suposição que
motivou o adiamento (precisa de Redis) estava certa só pro caso de
múltiplos processos, que não é o caso agora — implementado com uma
única dependência nova (`slowapi`, que só traz `limits` junto).

Aplicado em `app/api/v1/auth.py`: `/register` e `/refresh` 10/minuto,
`/login` 10/minuto (complementa, não substitui, o bloqueio por CONTA
já existente desde a ETAPA 6 — aquele impede força bruta contra uma
conta específica, este impede um IP de testar senha contra MUITAS
contas), `/password-reset/request` 5/minuto (mais apertado por gravar
no banco a cada chamada), `/password-reset/confirm` 10/minuto. Só
ativo com `ENVIRONMENT=production` (`app/core/rate_limit.py`) — em
dev/test atrapalharia sem proteger nada real, e a própria suíte bate
dezenas de vezes por minuto nas mesmas rotas de propósito.

### CI

`.github/workflows/ci.yml`: um job pro backend (Postgres efêmero via
`services:`, `alembic upgrade head`, `pytest --cov`) e um pro
frontend (`npm ci && npm run lint && npm run build && npm test`),
independentes um do outro. E2E (Playwright) fica de fora do CI por
decisão de escopo registrada no próprio arquivo: precisaria subir
backend+Postgres dentro do CI também (viável, mas dobra o tempo de
cada rodada) — mantido como responsabilidade de rodar manualmente
antes de um release até que o volume de PRs justifique o custo.

### Artefatos de deploy

**Backend** (`backend/Dockerfile`): virou a imagem de PRODUÇÃO por
padrão (sem `--reload`, usuário não-root, `--workers` configurável
via `WEB_CONCURRENCY`) — `docker-compose.yml` (dev) agora sobrescreve
`command:` com `--reload` por cima da mesma imagem, em vez de manter
dois Dockerfiles pra sincronizar manualmente.

**Frontend** (`frontend/Dockerfile`, novo): build multi-stage — Vite
compila o bundle estático, nginx serve (`frontend/nginx.conf` com
`try_files ... /index.html`, necessário pras rotas do
`react-router-dom` sobreviverem a F5/link direto). `VITE_API_BASE_URL`
entra como build ARG porque o Vite grava esse valor DENTRO do JS
compilado — documentado em `docs/deploy.md` que trocar de domínio
exige rebuild, não só reiniciar o container.

**`docker-compose.prod.yml`** (novo): sem bind-mount de código, sem
expor a porta do Postgres pro host, mais um serviço `caddy` na frente
cuidando de HTTPS automático (Let's Encrypt) — escolhido especificamente
por não precisar configurar certbot/renovação na mão, o tipo de
peça operacional que combina com "não complicar sem necessidade" já
registrado neste projeto pra outras escolhas de infraestrutura.

**`backend/.env.production.example`** (novo): modelo com todas as
variáveis que produção precisa e dev não força a preencher (SMTP
real, `FRONTEND_URL`/`CORS_ORIGINS` com o domínio de verdade,
`POSTGRES_PASSWORD` — nunca a de dev) — inclui o lembrete de que a
aplicação recusa subir com `JWT_SECRET_KEY` no valor de exemplo
(guard da ETAPA 30-32) de propósito, não é bug.

### Dois achados reais corrigidos antes de considerar pronto

Nenhum dos dois foi assumido — descobertos testando de verdade
(`docker build`, com o daemon do Docker disponível nesta sessão):

1. **`.dockerignore` ausente em ambos os serviços.** Sem ele,
   `COPY . .` no Dockerfile do backend copiaria o `backend/.env`
   LOCAL (com segredo de verdade, se configurado) pra dentro de uma
   camada da imagem — permanente mesmo que apagado depois (camadas
   de imagem Docker são imutáveis), e vazaria se a imagem fosse
   publicada num registry. No frontend, o mesmo `COPY . .` copiaria o
   `node_modules` do HOST por cima do que o `npm ci` acabara de
   instalar dentro do container, um risco real de drift entre
   lockfile e o que fica instalado na imagem. Corrigido com
   `.dockerignore` em cada serviço.
2. **`CMD` do backend na forma "shell"** (`CMD uvicorn ...` sem
   colchetes) — o próprio `docker build` avisou
   (`JSONArgsRecommended`): nessa forma o uvicorn roda como filho do
   `/bin/sh`, que não repassa `SIGTERM` de forma confiável — um
   `docker stop`/redeploy esperaria o timeout inteiro e mataria à
   força em vez de encerrar graciosamente conexões em andamento.
   Corrigido pra `CMD ["sh", "-c", "exec uvicorn ..."]` — o `exec`
   troca o processo do shell pelo do uvicorn (mesmo PID), que passa a
   receber o sinal direto. Padrão conhecido, não invenção desta
   sessão.

### Verificação (não assumida — executada)

- `pytest -q` → **225 passed** (223 + 2: mecanismo de rate limit
  provado contra uma app mínima isolada — decorator + middleware +
  exception handler devolvendo 429 depois do limite —, e que o
  limiter de produção fica `enabled=False` fora de `ENVIRONMENT=
  production`).
- Smoke test manual ao vivo (fora do pytest, contra a app real):
  `ENVIRONMENT=production` + 12 chamadas seguidas a `POST
  /auth/register` → as 10 primeiras `201`, a 11ª e 12ª `429`. Contas
  de teste removidas do banco de dev depois.
- `docker compose -f docker-compose.prod.yml config` validado (com
  variáveis de exemplo) — YAML e interpolação de variáveis corretos.
- `docker build` do backend executado de verdade contra um daemon
  Docker desta sessão — chegou a instalar dependências (falhou só no
  passo de rede do `pip install`, limitação da própria sandbox de
  desenvolvimento, não do Dockerfile) e foi o que revelou os dois
  achados acima antes de embalar a etapa como pronta. Build completo
  ponta a ponta (imagem funcional rodando) fica pra quando isto for
  testado num servidor real com acesso de rede normal — registrado
  aqui como verificação pendente, não escondido.
- `Caddyfile` revisado à mão depois de notar que `/health` (fora do
  prefixo `/api/v1` desde a ETAPA 3) não seria alcançado pela regra
  `/api/*` — corrigido antes de virar um problema de operação
  ("como eu confirmo que subiu?" sem resposta).

### Decisões de escopo registradas (não incluído nesta etapa)

Backup automático do Postgres, monitoramento/alertas de
infraestrutura, e deploy automático a partir do CI — todos fora de
propósito: os dois primeiros muitos provedores já oferecem de
fábrica (avaliar antes de construir um), e o terceiro depende de qual
servidor for escolhido, decisão que continua com o usuário. Ver
`docs/deploy.md`, seção "O que NÃO está incluído".

---

## 2026-09-12 — ETAPA 33-34: testes completos e correção de bugs

### Escopo desta etapa

Diferente de "escrever mais testes até cansar": instalado
`pytest-cov` (novo, `requirements.txt`) pra medir cobertura de
verdade em vez de confiar em impressão — e ir atrás só do que a
métrica apontasse como lacuna REAL (comportamento de produto nunca
exercitado), não perseguir 100% artificialmente. Cobertura de partida:
95% (3732 linhas, 171 não cobertas). Ao final: **97%** (3726 linhas —
caiu por causa da remoção de código morto abaixo —, 112 não
cobertas). As linhas restantes descobertas manualmente (amostra:
`auth_service.py` reautenticando um refresh token expirado de
verdade, `reset_password` com usuário apagado no meio do fluxo) são
ramos defensivos que o próprio schema já torna praticamente
inalcançáveis (`ON DELETE CASCADE`, soft delete nunca remove o
usuário) — escrever teste artificial só pra forçar a linha seria
cobertura de vaidade, não achado real; decisão de parar aqui.

### Código morto encontrado e removido

`checkin_service.get_checkin_by_id` — função completa, nunca chamada
por nenhuma rota nem por nenhum outro lugar do código (confirmado via
grep antes de remover). Mesma categoria recorrente de achado desta
sessão (peça "pré-modelada" sem uso), só que ao contrário desta vez:
não tinha nenhum item do documento de referência pedindo ela, então
em vez de implementar o uso removeu a função — `import uuid`
consequentemente também removido de `checkin_service.py` (só existia
por causa do type hint dela).

### Lacunas reais de teste fechadas (7 testes novos, todos batendo em comportamento de produto nunca exercitado antes)

- **Tarefas**: só `GET /tasks/{id}` tinha teste de "404 pra tarefa de
  outra pessoa" — as outras 7 rotas mutantes
  (`PATCH`/`start`/`pause`/`resume`/`postpone`/`complete`/`cancel`/
  `events`) nunca tinham sido verificadas nesse caminho. Relevante
  porque é comportamento de AUTORIZAÇÃO, não só UX — um `except`
  esquecido numa rota nova vazaria a existência da tarefa via 409 em
  vez de 404.
- **Medicamentos**: mesmo padrão — 5 das 8 rotas mutantes nunca
  tinham teste de posse. Também descoberto: `ScheduleNotFound` (um
  `schedule_id` válido mas pertencente a OUTRO medicamento do mesmo
  usuário) nunca tinha sido exercitado em nenhuma das 3 rotas que
  distinguem esse erro de `MedicationNotFound`.
- **Medicamentos, caminho de sucesso**: `update_schedule` (editar
  horário de uma dose já cadastrada), `list_events_for_schedule`
  (listar adesão de UM horário específico, não todos do medicamento)
  e `list_schedules` (listar os horários de um medicamento) nunca
  tinham sido chamados com sucesso por nenhum teste — só o 404.
- **Check-in**: filtro `date_from`/`date_to` de `GET /checkins`
  (histórico por período) nunca tinha sido testado.
- **Painel analítico, estatística de intervenção**: só o ramo
  `helped=True` tinha teste — `not_helped_count` e `no_result_count`
  nunca tinham sido verificados. Relevante porque é a contagem que a
  pessoa vê pra saber "o que tem funcionado" — uma inversão de lógica
  ali reportaria efetividade enganosa, silenciosamente. Rodado:
  lógica already estava certa, mas agora está **provada** certa, não
  só assumida.
- **`Strict-Transport-Security` em produção** (middleware da ETAPA
  30-32): o branch `environment == "production"` nunca tinha sido
  exercitado — nenhum teste roda com esse valor. Testado via
  `monkeypatch` no objeto `settings` já carregado por `app.main`, sem
  precisar reconstruir a aplicação inteira.

### Verificação (não assumida — executada)

- `pytest -q` → **223 passed** (215 no fim da ETAPA 30-32 + 8 novos:
  varredura de 404 em tarefas, varredura de 404 em medicamentos,
  `ScheduleNotFound` por medicamento trocado, `update_schedule` e
  `list_schedules`/`list_events_for_schedule` no caminho de sucesso,
  filtro de check-in por período, e o branch de HSTS em produção do
  middleware da ETAPA 30-32 — mais um teste já existente de
  estatística de intervenção ampliado com os dois ramos que faltavam,
  não contado como novo).
- `pytest --cov=app --cov-report=term-missing` rodado antes e depois
  — 95%→97%, com a lista de linhas restantes revisada manualmente
  (não só olhada de relance) pra confirmar que são defensivas, não
  lacunas de produto.

---

## 2026-09-12 — ETAPA 30-32: revisão de segurança, UX e performance

### Escopo desta etapa

Diferente das etapas anteriores (construir feature nova), esta é uma
auditoria do que já existe: ler o código com olho crítico procurando
o que uma sessão de desenvolvimento rápido tende a deixar passar —
sem adicionar complexidade nova, só fechar lacunas reais. Quatro
frentes: segurança, banco de dados/performance, UX/acessibilidade, e
uma decisão de escopo explícita sobre o que **não** foi construído.

### Segurança — 3 achados reais corrigidos

**1. Reuso de refresh token já rotacionado não era tratado como sinal
de roubo de sessão.** Desde a ETAPA 6, o próprio docstring de
`rotate_refresh_token` já dizia: "se o dono legítimo tentar usar o
token antigo depois, o pedido falha e (em uma iteração futura) pode
disparar alerta de possível roubo de sessão" — a "iteração futura"
nunca tinha chegado. `_get_active_refresh_session` agora distingue
dois casos que antes caíam no mesmo `InvalidRefreshToken` genérico:
token que nunca existiu ou expirou (erro comum) vs. token que existe
mas já está `revoked_at` (foi trocado numa rotação anterior — reuso
dele é sinal de cópia roubada em uso, já que o dono legítimo não
deveria mais possuir esse valor). No segundo caso, revoga **toda**
sessão ativa do usuário — reaproveitando `revoke_all_sessions`, a
mesma função já usada em troca de senha e desativação de conta, não
uma nova — e grava `AuditLog` com a ação nova `SUSPECTED_SESSION_THEFT`
antes de levantar `RefreshTokenReused` (subclasse de
`InvalidRefreshToken` de propósito: a rota continua respondendo o
mesmo 401 genérico, pra não confirmar pro possível atacante que a
detecção disparou). Testado: reusar o token antigo derruba até o
token novo, emitido pela própria rotação legítima segundos antes
(`test_reusing_an_already_rotated_refresh_token_revokes_the_whole_session_family`),
e a auditoria grava exatamente uma linha
(`test_reusing_a_rotated_refresh_token_writes_audit_log`).

**2. Nenhum cabeçalho de segurança de resposta HTTP.** Adicionado
`security_headers_middleware` em `app/main.py`:
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: strict-origin-when-cross-origin` em toda resposta;
`Content-Security-Policy` diferenciada — `default-src 'none'` nas
rotas de API (JSON puro, nunca deveria executar script nenhum) e uma
CSP mais permissiva só em `/docs`/`/redoc` (que carregam JS do CDN
jsdelivr pra renderizar o Swagger UI); `Strict-Transport-Security` só
quando `environment == "production"` (em dev/http o header não faz
sentido e só atrapalha inspecionar respostas locais).

**3. Nada impedia subir em produção com os defaults inseguros.** Os
comentários em `config.py` já avisavam que `jwt_secret_key` e `debug`
precisam ser sobrescritos em produção — mas isso nunca foi verificado
de verdade, um `ENVIRONMENT=production` sem as outras variáveis
simplesmente funcionaria com o segredo de JWT público (versionado
neste repositório) e com `debug=True` (que tende a vazar stack trace
em resposta de erro). Um `model_validator` em `Settings` agora recusa
inicializar (`ValueError`, falha rápido e alto) quando
`environment == "production"` e `jwt_secret_key` ainda é o valor de
fábrica, ou quando `debug` está ligado. Não se aplica fora de
produção — dev/test continuam livres pra usar os defaults, como
sempre foi.

**Revisado e mantido como está**: hashing de senha (Argon2) e de
token opaco (SHA-256, de propósito — o token já nasce com entropia
alta, não precisa de uma função lenta contra força bruta) em
`core/security.py`; bloqueio de conta por tentativa de login errada
(item 35, já sólido desde a ETAPA 6). Nenhuma mudança necessária ali.

### Banco de dados — 2 índices reais faltando

Toda coluna `user_id` de toda tabela já tinha índice desde o começo —
boa disciplina mantida por 26+ etapas. Mas duas colunas de
relacionamento usadas em filtro direto (`WHERE coluna == valor`)
tinham ficado sem: `Observation.relationship_id`
(`trust_service.list_observations`) e
`Intervention.support_relationship_id` (`dashboard_service` e
`intervention_service`, pra achar pedido de apoio/body doubling
pendente). Corrigido nos models e na migration existente
(`47f79baac7ca_modelo_de_dados_completo.py` — este projeto ainda não
tem migration incremental de verdade; até aqui, toda mudança de
schema foi feita editando essa única migration e recriando o banco de
dev, prática que só deixa de fazer sentido quando existir dado de
produção real pra preservar, na ETAPA 35). Ciclo
`upgrade → downgrade → upgrade` revalidado, e
`alembic revision --autogenerate` confirmado retornando diff vazio
(prova de que a migration bate exatamente com os models).

**N+1 revisado, não corrigido de propósito**: `_medications_today`
(`dashboard_service.py`) faz uma query por medicamento agendado pra
achar a dose de hoje, e mais uma pra ler o nome do medicamento —
tecnicamente um N+1. Decisão: manter como está. O "N" aqui é o número
de medicamentos ativos de UMA pessoa (tipicamente 1-5, não centenas)
— não é o formato de N+1 que degrada com escala, é um punhado de
queries indexadas em milissegundos, uma vez por carregamento do
painel diário. Resolver com `joinedload`/batch adicionaria
indireção real por um ganho não mensurável neste volume — trade-off
contra o próprio princípio de não complicar sem necessidade do
projeto.

### UX/acessibilidade — revisado, adequado, sem mudança

Verificado especificamente pensando em quem vai usar o app com baixa
função executiva (ansiedade, TDAH, depressão) — provavelmente pelo
celular, nem sempre com atenção plena: `viewport` meta presente desde
o início; 41 usos de `aria-label`/`role` espalhados por 21 arquivos
(rótulos acessíveis não foram esquecidos); CSS majoritariamente em
unidades relativas, sem `min-width` fixo problemático, com um
breakpoint em 480px que ajusta fonte/cabeçalho pra tela pequena.
Build de produção: 349KB (101KB gzip) num chunk único, sem
code-splitting por rota — tamanho normal pra uma SPA React deste
porte; dividir em chunks por rota adicionaria complexidade real
(waterfall de rede extra) por uma economia que não justifica nesta
fase. Nada aqui pedia correção.

### Decisão de escopo registrada: rate limit por IP, adiado

Proteção por IP contra força bruta/abuso na borda (além do bloqueio
por conta já existente) fica **fora** desta etapa, de propósito — o
próprio texto da ETAPA 6 já registrava isso como a "camada que falta
quando o volume justificar". Adicionar rate limit por IP de verdade
pede infraestrutura compartilhada entre processos (Redis, ou
equivalente) pra sobreviver a múltiplos workers/reinícios — exatamente
o tipo de peça que o projeto vem evitando adicionar sem necessidade
comprovada (mesma lógica já registrada contra Celery). Decisão:
revisitar quando a ETAPA 35 (ambiente de produção) definir a
infraestrutura de deploy real, ou antes disso se o volume de tráfego
justificar.

### Verificação (não assumida — executada)

- 215 testes de backend passando (209 antes desta etapa + 6 novos:
  reuso de refresh token revoga a sessão inteira, reuso grava
  auditoria, guard de produção rejeita segredo default, guard de
  produção rejeita `debug=true`, guard aceita config de produção
  válida, dev continua livre pro default).
- Ciclo `alembic downgrade base → upgrade head` revalidado depois da
  mudança de índices; `--autogenerate` confirmado sem diff pendente.
- Guard de produção testado também fora do pytest, instanciando
  `Settings(environment="production", debug=False)` sem segredo real
  — levanta `ValueError` com a mensagem certa antes de qualquer coisa
  subir.
- `npm run build` do frontend re-executado (nenhum arquivo de
  frontend mudou nesta etapa) só pra confirmar o tamanho de bundle
  citado acima.

---

## 2026-09-12 — ETAPA 29: suíte de testes automatizados de frontend

### Escopo desta etapa

Próxima da ordem depois da ETAPA 28. Até aqui a única garantia de que
o frontend funcionava de ponta a ponta era rodar manualmente um script
Playwright ad hoc por leva — útil pra verificar UMA vez, inútil como
proteção contra regressão depois que a sessão termina. Duas camadas
escolhidas, cada uma cobrindo o que a outra não cobre bem:

**Vitest + React Testing Library** (unit/componente, sem servidor,
segundos pra rodar) — `vitest.config.ts` separado de `vite.config.ts`
de propósito (esse último é lido por `tsc -b`/`vite build`, que não
conhecem os tipos de `vitest/config`; misturar arriscaria quebrar o
build de produção por causa de config de teste).

**Playwright commitado** (`frontend/e2e/`, `playwright.config.ts`) —
formaliza os scripts ad hoc mais valiosos desta sessão em specs que
sobrevivem à sessão. `webServer` no config sobe backend+frontend
sozinho (pré-requisito: Postgres já rodando e `backend/.venv` já
criado — mesmo pré-requisito de rodar a aplicação manualmente).

### O que foi construído

Unit/componente (25 testes, 5 arquivos):
- `api/client.test.ts` — `describeError` (ETAPA 28) nos 4 casos:
  `ApiError`, offline, `TypeError`, fallback específico.
- `components/ErrorBoundary.test.tsx` — renderiza filhos normalmente;
  mostra fallback + botão "Recarregar" quando um filho lança.
- `components/OfflineBanner.test.tsx` — aparece/some reagindo aos
  eventos `online`/`offline` do browser.
- `labels.test.ts` — a checagem mais valiosa do lote: um
  `Record<Union, string>` já é conferido pelo `tsc -b` (falta uma
  chave, o build quebra sozinho), mas um array `_ORDER` (usado pra
  ordenar `<option>` de select) NÃO é — um valor novo na union não
  obriga o array a acompanhar, e ninguém notaria até abrir aquele
  formulário específico. Teste compara as 9 chaves de cada `_ORDER`
  contra o `_LABELS` correspondente.
- `pages/TasksPage.test.tsx` — `TaskCard` exportado (era `function`
  interna, virou `export function`, nenhuma mudança de comportamento)
  e testado isoladamente por status: confere que só os botões válidos
  pra aquele estado aparecem (mapa de transição mora só no backend,
  ver ETAPA 27 8ª leva — este teste protege a metade que É de
  frontend: QUANDO mostrar cada botão).

E2E commitado (6 specs, 3 arquivos): cadastro + sessão sobrevivendo a
reload + logout; check-in parcial aceito e check-in vazio rejeitado;
ciclo de vida completo de tarefa (criar → iniciar → pausar → retomar →
adiar com motivo → concluir) e cancelamento com confirmação de dois
passos; convite → aceitar → só depois de permissão concedida a seção
correspondente aparece pro lado que recebe confiança (nunca antes).

### Decisões e achados no caminho

**Token de convite só existe no Postgres**: `RelationshipPublic` nunca
expõe `invite_token` de volta pra UI, e o cadastro v1 não manda e-mail
nenhum pro convite (só pra reset de senha, desde a ETAPA 22) — em
produção esse token chegaria por um canal fora do produto, ainda em
aberto. O teste E2E lê direto do Postgres local
(`e2e/helpers.ts:fetchInviteTokenFromDb`, mesmas credenciais fixas de
dev) pra simular esse canal, do jeito que os scripts ad hoc desta
sessão já precisavam fazer manualmente.

**Página do dono não recarrega sozinha quando o convidado aceita**:
achado ao escrever o teste — `TrustedPeoplePage` busca a lista de
relacionamentos uma vez, no mount; sem um `reload()` explícito depois
de a pessoa de confiança aceitar, o dono nunca vê o status virar
"accepted" nem o botão "Gerenciar permissões" aparecer. Não é um bug
(nenhum polling/websocket foi planejado pro MVP) — registrado aqui
porque quase virou um falso negativo no teste.

**Ambiente do sandbox usado nesta sessão** tem só um Chromium
pré-instalado, de build mais antigo do que a versão do
`@playwright/test` instalada tentaria baixar sozinha (sem acesso pra
baixar outro). Resolvido com uma variável de ambiente opcional
(`PLAYWRIGHT_CHROMIUM_PATH`, documentada no README) que só tem efeito
se setada — numa máquina normal, `npx playwright install chromium`
uma vez resolve sozinho e a variável fica sem efeito nenhum.

### Verificação

`npm run build`/`npm run lint` limpos (só os mesmos warnings
pré-existentes de `set-state-in-effect`). Backend não alterado, 207
testes intactos. Suíte nova: 25/25 unit/componente, 6/6 E2E — todas
rodadas de verdade contra backend e frontend reais nesta sessão, não
só escritas.

### Decisão de escopo registrada

Sem CI configurado ainda (GitHub Actions ou equivalente) — os testes
existem e rodam localmente, mas rodá-los automaticamente a cada mudança
é decisão de infraestrutura, mais alinhada com a ETAPA 35 (ambiente de
produção) do que com "os testes existem" desta etapa. Próxima etapa:
30-32 (revisão de segurança/UX/performance).

---

## 2026-09-12 — ETAPA 28: estados de loading/erro/vazio/offline

### Escopo desta etapa

Com a ETAPA 27 (frontend) completa, a próxima da ordem de
implementação (`docs/decisions.md`, tabela das 36 etapas) é ETAPA 28:
garantir que toda tela cobre loading, erro, vazio e offline — nunca
uma tela em branco ou um erro cru. Auditoria antes de escrever
qualquer código (mesmo princípio de sempre confirmar antes de supor):
grep em `frontend/src/pages` mostrou que loading/erro/vazio já
seguiam um padrão consistente desde a 1ª leva — todo fetch de lista
usa `dado === null && !error` pra "carregando…", toda seção com lista
vazia já tem um texto próprio (ex.: `/observando` sem relacionamento
aceito, `/auditoria` sem registro). Os dois gaps REAIS encontrados:
nenhum tratamento de rede caída/servidor fora do ar (cada tela cai no
fallback genérico de texto fixo, sem diferenciar "seu problema" de
"problema de conexão"), e nenhum `ErrorBoundary` — um erro de render
inesperado em qualquer componente derrubava a aplicação inteira pra
tela branca, sem chance de recuperação sem F5 às cegas.

### O que foi construído

**`describeError(err, fallback)`** em `api/client.ts`: centraliza a
tradução de erro pra mensagem de tela. Prioridade: `ApiError.detail`
(mensagem do backend) → `!navigator.onLine` ou `TypeError` (o erro
típico de um `fetch` que nunca chegou a um servidor) → mensagem de
conexão genérica, mais útil que qualquer texto específico da tela
porque o problema não é dela → só then o `fallback` que a própria
chamada pedia antes. Substituiu mecanicamente as 40 ocorrências do
padrão antigo `err instanceof ApiError ? err.detail : "texto"` em 16
páginas + 2 componentes (script Python, verificado que cada arquivo
só usava `ApiError` nesse padrão exato antes de trocar o import —
nenhuma edição manual arriscando divergência de texto).

**`useOnlineStatus()`** (`hooks/`) + **`<OfflineBanner />`**
(`components/`, montado no `Layout`): escuta `online`/`offline` do
browser e mostra um aviso persistente assim que a rede cai, em vez de
deixar a pessoa descobrir só quando uma ação falhar. Não bloqueia
nada — dado já carregado continua na tela.

**`<ErrorBoundary />`** (única classe do frontend — `componentDidCatch`
não tem equivalente em hook ainda), envolvendo `<App />` inteira em
`main.tsx`: qualquer erro de render vira uma tela "Algo deu errado" com
botão de recarregar, em vez de branco sem explicação. Não loga em
lugar nenhum (sem serviço de telemetria no MVP) — só garante uma saída.

### Verificação

Backend não alterado; 207 testes reconfirmados intactos. Script
Playwright: banner de offline aparece navegando com a rede cortada e
some quando volta; uma ação de rede falhando mostra mensagem de
conexão amigável, nunca "Failed to fetch" cru; uma rota temporária
(`/__boom_test__`, removida antes do commit) forçando uma exceção de
render confirmou a tela de fallback do `ErrorBoundary` com o botão
"Recarregar" — 7/7 checagens. `npm run build`/`npm run lint` limpos
(warnings pré-existentes de `set-state-in-effect`, não introduzidos
por esta etapa).

### Decisão de escopo registrada

`navigator.onLine` só detecta a placa de rede desligada, não um
backend fora do ar com internet normal — para esse segundo caso, a
mensagem de conexão do `describeError` (via detecção de `TypeError`)
já cobre, sem precisar de sondagem periódica ao servidor (ping),
deliberadamente fora do escopo por ser complexidade desproporcional
pro MVP. Próxima etapa: ETAPA 29 (testes automatizados de frontend —
até aqui só scripts Playwright ad hoc rodados manualmente).

---

## 2026-09-12 — ETAPA 27 (oitava leva): tarefas + sugerir tarefa pela pessoa de confiança

### Escopo desta leva

O usuário aceitou seguir com "sugerir tarefa" (`SUGGEST_TASK`), a
última peça planejada da ETAPA 27. No caminho, uma checagem antes de
implementar revelou um problema de escopo real: a ETAPA 10 (tarefas,
máquina de estados `pending → started/paused/postponed → completed/
cancelled`) nunca ganhou NENHUMA tela em nenhuma leva anterior, e o
painel diário/analítico também não expõe tarefas. Construir só o
formulário de sugestão sem nenhum lugar pro dono ver ou agir sobre a
tarefa criaria um beco sem saída — a sugestão desapareceria pro dono
assim que criada. Decisão: esta leva cobre as duas coisas juntas —
`/tarefas` (dono) e o formulário de sugestão (pessoa de confiança) —
em vez de só a segunda, que sozinha não faria sentido como produto.

### O que foi construído

**`/tarefas`** (dono): criar tarefa (título, descrição, prioridade,
prazo), listar todas, e as ações da máquina de estados já existente
no backend desde a ETAPA 10 — iniciar, pausar, retomar, adiar (sempre
com motivo, nunca implícito no silêncio — mesmo princípio do item 8),
concluir, cancelar (motivo opcional). Cada botão só aparece quando a
transição é válida no estado atual (mapa de transições já existente
em `task_service.py`, não reinventado na UI). Tarefa de origem
`trusted_person_suggestion` mostra "sugerida por X", cruzando
`source_relationship_id` com a lista de relacionamentos do próprio
dono (`GET /trusted-people`) pra mostrar o rótulo — mesma decisão de
UI já registrada como pendente na ETAPA 26 pra auditoria, agora
aplicada aqui.

**Formulário "Sugerir uma tarefa"** na `TrustedDashboardPage`
(`/observando/:id`), condicionado à permissão `SUGGEST_TASK` — mesmo
padrão já usado pro formulário de observação na 6ª leva. Backend não
precisou mudar: `POST /trusted-people/{id}/tasks/suggest` já existia
desde a ETAPA 21, só sem UI.

### Verificação

Backend não alterado; 207 testes reconfirmados intactos. Script
Playwright com duas contas reais cobriu o ciclo completo: criar
tarefa → iniciar → pausar → retomar → adiar com motivo (contador de
adiamento aparece) → concluir; segunda tarefa cancelada com
confirmação de dois passos; pessoa de confiança sugere uma tarefa
pelo painel dela; dono vê a tarefa sugerida na própria lista com o
rótulo do relacionamento correto. 15/15 checagens, zero erro de
console.

### Decisão de escopo registrada

Com isso, a ETAPA 27 (frontend) fica completa — todas as telas
planejadas desde o início estão entregues e verificadas. Trabalho
restante conhecido: suíte de testes automatizados de frontend
(ETAPA 29, já registrada como pendente desde a 1ª leva).

---

## 2026-09-12 — ETAPA 27 (sétima leva): visualizador de auditoria

### Escopo desta leva

Última peça sem tela do frontend: `GET /audit-log` já existia por
completo desde a ETAPA 26 (paginação, `actor_is_self`, metadata
saneada) — esta leva foi só construir `/auditoria` em cima do que já
estava pronto, sem tocar backend nenhum.

### O que foi construído

`/auditoria`: lista paginada (50 por página, `Anterior`/`Próxima`
movendo `offset`; `Próxima` desabilita quando a página vem com menos
de 50 registros — sem contagem total exposta pela API, esse é o sinal
disponível de que não há próxima página), rótulo em PT-BR por
`AuditAction`, badge "não foi você" quando `actor_is_self=false` (sem
revelar qual pessoa de confiança, decisão do backend na ETAPA 26 —
não é algo pra a UI tentar contornar), e metadata renderizada como
pares chave/valor genéricos — nunca uma lista fixa de campos, porque
cada `AuditAction` tem uma forma de metadata diferente.

### Verificação

Backend não alterado; 207 testes reconfirmados intactos. Script
Playwright com conta real: gerou eventos de verdade (login, convite
enviado, troca de senha) e confirmou os três aparecendo na tela com
os rótulos certos, mais o estado de paginação (`Anterior` desabilitado
na primeira página, `Próxima` desabilitado com menos de 50 registros).
7/7 checagens, zero erro de console.

### Decisão de escopo registrada

Com isso, a ETAPA 27 fica completa exceto por sugerir tarefa
(`SUGGEST_TASK`) pela pessoa de confiança — a única ação de nível
"apoiar" ainda sem tela, adiada de propósito desde a 6ª leva por
precisar de um formulário de criação de tarefa endereçado a outra
conta, que não é um encaixe barato em nenhuma leva anterior.

---

## 2026-09-12 — ETAPA 27 (sexta leva): painel operacional da pessoa de confiança

### Escopo desta leva

Faltava a experiência de quem RECEBE confiança, não de quem a concede
— a segunda metade da rede de confiança (ETAPA 27, 2ª leva) só cobria
convidar, gerenciar permissões e aceitar um convite com uma tela de
confirmação textual; a pessoa de confiança nunca tinha um lugar pra
efetivamente acompanhar alguém. Escopo: lista de contas acompanhadas
("`GET /trusted-people/watching`", endpoint novo — não existia nem no
backend, ver abaixo), painel restrito por relacionamento (estado,
adesão a medicação, indicadores liberados, histórico de estado e de
desvio, plano de crise, pedidos de acompanhamento pendentes — cada
seção só se a permissão correspondente estiver concedida, dado que
`TrustedDashboard` já vinha pronto desde a ETAPA 23/24), registrar
observação pela UI (endpoint já existia desde a ETAPA 14/16, só sem
tela), e aceitar pedido de acompanhamento (`HELP_WITH_TASK`, primeiro
uso real da rota desde que foi criada na ETAPA 10).

Deliberadamente fora: sugerir tarefa (`SUGGEST_TASK`) — o endpoint já
existe, mas criar uma tarefa pra outra pessoa pelo formulário certo é
uma tela nova por si só, não um encaixe barato nesta leva — e o
visualizador de auditoria, que continua sem depender de nada aqui.

### Gap de backend descoberto e fechado

`GET /trusted-people` sempre existiu, mas só do ponto de vista do
DONO (relacionamentos que ele convidou). Não havia nenhuma rota pra a
PESSOA DE CONFIANÇA listar as contas que ela acompanha — sem isso, ela
precisaria já saber o UUID do relacionamento de cor pra abrir o
próprio painel, o que não faz sentido nenhum como fluxo real. Criado
`GET /trusted-people/watching` (service
`list_relationships_for_trusted_person`, schema
`RelationshipAsTrustedPublic`) filtrando por
`trusted_user_id == usuário atual` e `status == accepted`.

Esse endpoint precisou identificar o dono de forma legível pra pessoa
de confiança — `RelationshipPublic.invite_email` não serve, porque
esse campo é o e-mail de quem foi CONVIDADO (a própria pessoa de
confiança), não o do dono; um teste pego durante a implementação
confirmou isso na prática (o teste esperava o e-mail do dono e recebeu
o da pessoa de confiança de volta). Resolvido com
`owner_display_name`: vem do `Profile.display_name` do dono quando o
onboarding já foi feito, cai pro e-mail da conta dele quando ainda
não — nunca o e-mail do convite.

### O que foi construído

Backend: `RelationshipAsTrustedPublic` (schema),
`list_relationships_for_trusted_person` (serviço, resolve nomes em
lote — duas queries, nunca N+1), `GET /trusted-people/watching`
(rota). Frontend: `/observando` (lista de contas acompanhadas) e
`/observando/:relationshipId` (painel — reaproveita `StateBadge` e o
mesmo padrão de renderização condicional por seção já usado no
painel analítico do dono), link "Ver painel" na tela de aceitar
convite, e item de navegação "Pessoas que acompanho".

### Verificação

205 testes de backend + 2 novos (`test_trusted_person_sees_accepted_
relationship_in_watching_list`, `test_watching_list_excludes_pending_
invite_and_owner_view`) = 207 passando. Dois cenários Playwright
ponta a ponta com contas reais: (1) permissões concedidas —
14 checagens, incluindo o dono enxergando de volta a observação
registrada pela pessoa de confiança; (2) nenhuma permissão concedida
— 6 checagens confirmando que o painel abre mas cada seção sem
permissão simplesmente não aparece (nunca um erro, nunca "sem
permissão" repetido seção por seção). 20/20 no total, zero erro de
console.

### Decisão de escopo registrada

Falta só: visualizador de auditoria e sugerir tarefa
(`SUGGEST_TASK`) pela pessoa de confiança. Com isso, o frontend cobre
os dois lados da rede de confiança por completo — dono e pessoa de
confiança.

---

## 2026-09-12 — ETAPA 27 (quinta leva): plano pessoal e configurações de conta no frontend

### Escopo desta leva

Depois de auth+painel+check-in, rede de confiança, medicação+rotina, e
alertas+analítico, o que faltava pra "fechar o ciclo do dono da
conta" era o plano pessoal (item 19, "plano quando eu não perceber")
e as ações de conta (trocar senha, exportar dados, desativar conta —
LGPD, item 53). Nenhuma das quatro telas restantes (essas duas +
auditoria + painel da pessoa de confiança) dependia das outras — essa
dupla foi escolhida por ser a mais alinhada com fechar esse ciclo.

### O que foi construído

- **`/plano-pessoal`**: estado vazio com formulário de criação
  (título + descrição em texto livre) quando não há plano ativo;
  visualização + edição (PATCH) quando existe; lista de "sinais"
  (`PersonalPlanRule`) com formulário de adicionar (área + descrição
  do limiar nas palavras da própria pessoa — nunca um número, mesmo
  espírito de "nunca inventar limiar clínico" já registrado no motor
  de desvio) e um botão de desativar/reativar por sinal (reversível,
  sem confirmação de dois passos — diferente de desativar o plano
  inteiro); desativar o plano inteiro usa o mesmo fluxo de confirmação
  inline de duas etapas já padronizado nas outras telas, com o aviso
  de que não há reativação (mesma decisão de escopo já tomada no
  backend na ETAPA 25).
- **`/configuracoes`**: trocar senha (`POST /auth/change-password`,
  endpoint que existia desde a ETAPA 6 mas nunca tinha UI — primeiro
  uso real fora de testes/curl); exportar dados (`GET
  /account/export` — como o backend devolve um JSON síncrono sem
  `Content-Disposition`, o download é montado no próprio navegador via
  Blob, sem endpoint novo); desativar conta (`POST
  /account/deactivate`) — zona de perigo com confirmação de senha e
  fluxo de dois passos, redirecionando pra `/entrar` depois, reaproveitando
  o `logout()` já existente da store de auth só pra limpar o estado
  local (a sessão já foi revogada pelo backend nesse momento).

### Achado que vale registrar (não é bug, mesmo padrão já visto)

Dois "Failed to load resource 404" no console na primeira visita a
`/plano-pessoal` (confirmado com um listener de rede dedicado: duas
chamadas idênticas a `GET /personal-plan`, ambas 404 porque ainda não
existe plano). Mesma causa já documentada na 3ª leva pra
`/routines/current`: double-invoke do `useEffect` em React 19
StrictMode sobre uma leitura pura, sem efeito colateral — duplicar é
inofensivo, só ruído de log em desenvolvimento. Não corrigido de
propósito, pelo mesmo motivo já registrado lá.

### Verificação

Script Playwright com backend e frontend reais: estado vazio → criar
plano → editar título → adicionar sinal → desativar sinal (badge
"inativo" aparece, botão vira "reativar") → desativar o plano inteiro
com confirmação de dois passos → volta ao estado vazio → trocar senha
(confirmado também via chamada direta à API que a senha nova
funciona e a antiga não) → exportar dados (download real interceptado
pelo Playwright, JSON validado: contém a conta certa e reflete o
plano já desativado como `null`) → desativar conta com confirmação de
senha e dois passos → redireciona pra `/entrar` → confirmado via API
que o login com a conta desativada falha. 18/18 checagens de conteúdo
passaram (a 19ª checagem, "zero erro de console", foi reclassificada
pelo achado acima — não é uma falha real).

Backend não foi alterado nesta leva; suíte completa (205 testes)
reconfirmada intacta.

### Decisão de escopo registrada

Falta visualizador de auditoria e o painel operacional da pessoa de
confiança (aceitar pedido de acompanhamento, registrar observação
pela UI, ver o dashboard restrito) — nenhuma depende da outra, podem
vir em qualquer ordem na próxima leva. Com isso, o frontend do dono
da própria conta fica completo; o que resta depois disso é a
experiência da pessoa de confiança e a consulta de auditoria.

---

## 2026-09-12 — ETAPA 27 (quarta leva): alertas, explicabilidade e painel analítico no frontend

### Escopo desta leva

Depois de auth+painel+check-in, rede de confiança, e medicação+rotina,
a próxima prioridade é a parte do produto que mostra o "porquê" por
trás do estado verde/amarelo/vermelho — até aqui só existia como API.
Sem isso, o usuário via a cor do estado no painel diário mas não
conseguia entender ou revisar o motivo.

### O que foi construído

- **`/alertas`**: estado atual (reaproveita `StateBadge`), "Ver por
  que estou nesse estado" (busca `GET /alerts/{id}/explanation`),
  "Já vi" / "Marcar como resolvido", histórico de alertas passados, e
  "Recalcular agora" (`POST /deviation/run` seguido de `POST
  /alerts/sync`, o mesmo par que o ciclo noturno do `scheduler_service`
  já roda sozinho desde a ETAPA 22 — aqui é só o mesmo botão manual
  que a API sempre ofereceu).
- **`/painel-analitico`**: seletor de período (7/30/90/365 dias),
  linha do tempo de estado, tendência por indicador, linha do tempo
  de desvio (com "Ver detalhes" por evento), adesão a medicação
  agregada, estatística de intervenções — tudo vindo de `GET
  /dashboard/analytics`.
- **Decisão de design deliberada sobre explicação e histórico**: a
  maioria dos textos (`label`, `explanation`, `reason_summary`)
  já vem pronta em PT-BR do backend — o frontend só organiza, nunca
  traduz ou recalcula, mesmo princípio do `explainability_service`.
  Mais importante: **o botão "Ver explicação" só aparece pro alerta
  ATUAL, nunca pra um item do histórico**. Motivo, confirmado lendo
  `explainability_service.explain_alert`: essa rota reconstrói a
  explicação a partir dos motores **atualmente** ativos, não uma
  foto do que causou aquele alerta especificamente no passado (é uma
  decisão de escopo do próprio backend, documentada na docstring do
  service) — oferecer "explicar" num alerta antigo mostraria dados
  de agora com a cara de "foi isso que causou aquilo lá atrás", o
  que seria enganoso. Já a explicação de um evento de desvio
  específico (`GET /deviation/events/{id}/explanation`, usada no "Ver
  detalhes" da linha do tempo de desvio no painel analítico) É fiel
  ao momento em que foi calculada — o `baseline_snapshot` é um
  retrato congelado — por isso essa sim aparece pra qualquer item do
  histórico.

### Verificação

Backend não alterado; suíte completa (205 testes) reconfirmada
intacta. Verificação de frontend em duas etapas: (1) fluxo com
usuário sem nenhum dado — confirma que a ausência de alerta/desvio
não quebra a tela (estados vazios corretos); (2) fluxo com um
`DeviationEvent`+`Alert` amarelo inseridos diretamente no Postgres
(simulando o que o ciclo noturno geraria organicamente após dias de
dados reais) — confirma explicação mostrando o motor e os
indicadores certos, "Já vi"/"resolver" funcionando, histórico
refletindo a mudança, painel analítico mostrando a mesma linha do
tempo e "Ver detalhes" do evento de desvio funcionando. 12/12
checagens, zero erro de console. Uma rodada inicial teve 2 falhas por
checar o texto da página antes do fetch assíncrono terminar (mesma
classe de erro de timing já vista na 1ª leva) — corrigido esperando
por um seletor de conteúdo real antes de ler o texto, não um
`<div>` genérico que já existe antes do dado chegar.

### Decisão de escopo registrada

Falta: editor de plano pessoal, configurações de conta, visualizador
de auditoria, painel operacional da pessoa de confiança. Nenhuma
dessas quatro depende das outras — próxima leva pode pegar qualquer
uma; a mais alinhada com "fechar o ciclo do dono da conta" é
plano pessoal + configurações de conta (exportar dados, desativar
conta), deixando auditoria e o painel da pessoa de confiança pra
depois.

---

## 2026-09-12 — ETAPA 27 (terceira leva): medicação e rotina no frontend

### Escopo desta leva

Depois de auth+painel+check-in (1ª leva) e rede de confiança (2ª
leva), a prioridade de valor era completar o outro lado do check-in
diário: medicação (o painel diário já mostrava a dose do dia, mas não
havia como cadastrar um medicamento nem confirmar a dose) e rotina de
referência (a base de comparação do próprio baseline, declarada só
uma vez no onboarding e nunca exposta numa tela).

### O que foi construído

- **`/medicamentos`**: cadastrar medicamento (nome, como tomar,
  anotações, lembrete on/off), adicionar horário por medicamento
  (hora + dias da semana ou "todo dia"), descontinuar (confirmação
  inline, mesmo padrão da revogação de acesso da 2ª leva).
- **Painel diário reforçado**: a dose de hoje que antes só EXIBIA o
  status agora deixa CONFIRMAR direto ali — "Tomei" grava na hora;
  qualquer outro status (não tomei / pulei de propósito / não tinha
  disponível) abre um seletor com os 8 motivos do backend
  (`MedicationSkipReason`) antes de confirmar, porque o schema exige
  motivo pra todo status que não seja "tomado". Esse é o loop que
  mais se repete no dia a dia — vale mais a pena resolver ali do que
  só na tela de gerenciamento.
- **`/rotina`**: estado vazio com formulário de criação quando ainda
  não existe rotina declarada; resumo + edição (PATCH, "ajuste
  corriqueiro") quando existe; "Começar nova versão" separado e com
  aviso — é a virada de vida do backend (`POST
  /routines/new-version`), fecha a versão atual e começa do zero,
  não é a mesma operação que editar. Formulário único
  (`RoutineForm`) reaproveitado nos três casos (criar, editar, nova
  versão) — todos os 12 domínios de ativação como checkboxes, os
  campos booleanos opcionais como select de 3 estados (sim/não/não
  informado) pra preservar `null` sem forçar uma escolha.
- **Eventos de vida** na mesma tela: listar e registrar (tipo,
  datas, descrição) — contexto pra não confundir uma transição de
  vida real com deterioração no motor de desvio.

### Verificação

Um script Playwright cobrindo o ciclo completo com backend e
frontend reais: criar medicamento → adicionar horário → dose aparece
no painel diário → confirmar "Tomei" → status atualiza na hora →
descontinuar → rotina inexistente mostra formulário → criar rotina →
resumo mostra os campos certos → editar → mudança persiste → registrar
evento de vida → aparece na lista. 10/10 checagens de conteúdo.

Achado que vale registrar (não é bug): dois `Failed to load resource
404` no console durante a navegação pra `/rotina` na primeira visita.
Investigado com um listener de rede dedicado — são duas chamadas
IDÊNTICAS a `GET /routines/current`, ambas 404 (esperado: ainda não
existe rotina), disparadas pelo mesmo double-invoke do `useEffect` em
StrictMode já visto na 1ª leva. Diferença importante em relação ao
bug do refresh token: aqui a chamada é uma leitura pura sem efeito
colateral (não invalida nada, não muda estado no servidor), então
duplicar é inofensivo — só ruído de log em desenvolvimento, não em
produção (`StrictMode` só dobra efeitos em dev). Não corrigido de
propósito: adicionar uma trava `useRef` só pra isso seria
complexidade sem ganho real, dado que o efeito é idempotente.

Backend não foi alterado nesta leva; suíte completa (205 testes)
reconfirmada intacta.

### Decisão de escopo registrada

Falta: alertas/explicabilidade, painel analítico, editor de plano
pessoal, configurações de conta, visualizador de auditoria, e o
painel operacional da pessoa de confiança. Próxima prioridade:
alertas/explicabilidade e painel analítico — são a parte do produto
que mostra o "porquê" por trás do estado verde/amarelo/vermelho, e
até aqui só existem como API.

---

## 2026-09-12 — ETAPA 27 (segunda leva): rede de confiança no frontend

### Escopo desta leva

Depois da primeira leva (auth + painel diário + check-in), a tela com
maior valor pra construir em seguida é a **rede de confiança**: é o
diferencial central do produto (notificar pessoas de confiança
segundo permissões granulares) — sem ela, o app só registra dados
sobre uma pessoa, não conecta ninguém. Medicação, rotina, alertas e
o resto continuam pra próximas levas, na ordem já registrada no
status geral abaixo.

### O que foi construído

- **`/rede-de-confianca`** (dono da conta): formulário de convite
  (e-mail + apelido opcional pra pessoa, ex. "minha irmã"), lista das
  pessoas convidadas com status (pendente/ativo/revogado), editor de
  permissões por relacionamento (as 13 `PermissionKey` do backend,
  cada uma com rótulo em PT-BR — `src/labels.ts` centraliza esses
  mapeamentos pra não duplicar em cada tela), e visualização das
  observações que essa pessoa registrou sobre o dono.
- **`PermissionEditor`** (`src/components/PermissionEditor.tsx`):
  estado local editável inicializado a partir do relacionamento,
  sincronizado de novo só quando o pai recebe uma resposta nova da
  API (nunca durante edição em andamento — evita perder edição não
  salva por um re-render do componente pai). Ao marcar
  `view_specific_indicators`, abre uma sub-lista com os 15
  `IndicatorKey` pra escolher escopo — único caso em que uma
  permissão carrega dado além de ligado/desligado. "Salvar" sempre
  manda o estado completo das 13 permissões pro PUT: confirmado
  contra `trust_service.update_permissions` que isso é seguro
  (upsert por chave, só gera `AuditLog` pras que realmente mudaram de
  valor — nunca sobrescreve permissões não incluídas, então mandar
  as 13 de uma vez não corre risco de "resetar" nada por engano).
- **`/aceitar-convite`**: tela simples pra quem recebeu um convite
  colar o código e aceitar. Decisão de escopo: só a confirmação
  textual do aceite fica nesta leva — a experiência operacional da
  pessoa de confiança (registrar observação, ver o painel restrito,
  aceitar pedido de acompanhamento) é o "painel da pessoa de
  confiança" já listado como pendente, não desta leva.
- **Revogação sem `window.confirm`**: um diálogo nativo de
  confirmação trava a aba e não combina com o tom "Companheiro
  calmo" da interface — o botão "Revogar acesso" vira um passo de
  confirmação inline ("Sim, revogar" / "Cancelar") em vez de um
  popup do navegador.

### Verificação

Dois scripts Playwright novos, ambos com backend e frontend reais
rodando simultaneamente (não só `npm run build`):

1. **Fluxo completo dono + pessoa convidada em duas abas
   (`BrowserContext` separados)**: registro dos dois → convite →
   token de convite lido direto do Postgres (sem servidor de e-mail
   de verdade no ambiente de teste) → aceite pela pessoa convidada →
   dono vê o relacionamento como "Ativo" → concede duas permissões,
   incluindo escopo de indicador específico → salva → confirma que a
   permissão persiste depois de um reload de página → revoga com o
   fluxo de dois passos → confirma status "Revogado". 9/9 checagens,
   zero erro de console.
2. **Observação ponta a ponta**: concede `record_observation` via
   API, a pessoa de confiança registra uma observação via API (a UI
   de registrar observação é do "painel da pessoa de confiança",
   ainda não construído), e confirma que ela aparece corretamente
   pro dono na tela de rede de confiança (categoria e nota em
   PT-BR). 4/4 checagens.

Backend não foi alterado nesta leva — suíte completa (205 testes)
confirmada intacta antes de entregar.

### Decisão de escopo registrada

O que falta continua grande: medicação, rotina, alertas/
explicabilidade, editor de plano pessoal, configurações de conta,
visualizador de auditoria, painel analítico, e o painel operacional
da pessoa de confiança (aceitar pedido de acompanhamento, registrar
observação pela UI, ver o dashboard restrito). Ordem de prioridade
decidida por valor: medicação/rotina em seguida (completam o
check-in diário), depois alertas/analítico, depois o resto.

---

## 2026-09-12 — ETAPA 27 (primeira leva): frontend React conectado ao backend

### Escopo desta leva — registrado explicitamente

ETAPA 27 é grande demais pra uma entrega só: o backend já tem ~30
rotas de domínio (auth, check-ins, rotina, medicação, baseline,
desvio, alertas, intervenções, notificações, dashboards, plano
pessoal, conta, auditoria, rede de confiança). Construir tela pra
cada uma de uma vez, sem checar direção com o usuário, seria o tipo
de "acumular módulo sem testar" que o próprio projeto evita desde a
ETAPA 3. Esta primeira leva prova a conexão ponta a ponta de verdade
— stack, autenticação, uma tela real de dado, um fluxo de escrita — e
para aí, deliberadamente, antes de continuar pras próximas telas.

### O que foi construído

- **Vite + React 19 + TypeScript**, scaffold em `frontend/`, sem
  framework de UI (CSS próprio — decisão de escopo: Tailwind ou
  similar só se a folha de estilo à mão começar a doer, item "evite
  overengineering"). `react-router-dom` pra rotas, `zustand` pra
  estado de autenticação (único store desta leva; cada tela busca seu
  próprio dado com `useEffect`, sem cache de servidor tipo React
  Query ainda — revisitar se duplicação de chamada virar problema).
- **Cliente de API em 3 camadas**: `client.ts` (fetch cru + tradução
  de erro do FastAPI pra mensagem exibível) → `apiFetch.ts` (injeta
  o access token e faz UM retry automático se a resposta vier 401,
  renovando via refresh token antes de desistir) → módulos por
  domínio (`api/auth.ts` embutido na store, `api/dashboard.ts`,
  `api/checkins.ts`). Tipos TS escritos à mão espelhando os schemas
  Pydantic usados (decisão: um gerador de tipos a partir do OpenAPI
  só se paga quando a superfície consumida crescer bastante).
- **Autenticação completa**: registro, login, logout, e RENOVAÇÃO
  SILENCIOSA da sessão ao recarregar a página — access token só em
  memória (nunca em `localStorage`, reduz o que um XSS rouba de forma
  persistente), refresh token em `localStorage` (sobrevive a F5,
  rotacionado a cada uso pelo próprio backend desde a ETAPA 6).
- **Duas telas reais**: painel diário (`GET /dashboard/daily` —
  estado atual com o mesmo verde/amarelo/vermelho do backend, status
  do check-in de hoje, medicação do dia, intervenções em andamento,
  contagem de notificações) e o formulário de check-in (`POST
  /checkins`, os 7 indicadores opcionais em escala 1-5, mesma regra
  de "pelo menos um preenchido" do backend refletida no cliente).

### Bug real de concorrência encontrado e corrigido antes de qualquer teste manual

O `StrictMode` do React 19 invoca todo efeito duas vezes em
desenvolvimento — isso faria dois `POST /auth/refresh` concorrentes
dispararem ao carregar a página, os DOIS com o MESMO refresh token
armazenado. Como o backend ROTACIONA o refresh token a cada uso
(invalida o anterior), a segunda chamada chegaria com um token já
invalidado pela primeira e derrubaria a sessão por engano — sessão
que tinha acabado de ser validada com sucesso pela primeira chamada.
Corrigido com uma guarda (`useRef`) em `main.tsx` que garante uma
única chamada de inicialização por carregamento de página. Confirmado
ao vivo com Playwright contando as requisições de rede: sem a guarda
seriam 2 chamadas a `/auth/refresh` no reload, com a guarda é 1.

### Verificação — Playwright, não só `npm run build`

`tsc -b && vite build` sem nenhum erro de tipo, `oxlint` só com 2
avisos não-bloqueantes (padrão esperado de busca-de-dado em
`useEffect`, revisitar quando/se entrar uma camada de cache de
servidor). Isso prova que compila, não que funciona — o Chromium
pré-instalado neste ambiente permitiu rodar um teste ponta a ponta de
verdade contra o backend real (Postgres + FastAPI + Vite dev server,
todos rodando juntos): registro → painel mostra verde/sem check-in →
preenche e envia check-in → painel reflete o check-in feito →
recarrega a página e a sessão sobrevive (renovação silenciosa) →
logout → login de novo. Mais um teste dedicado confirmando que uma
resposta 401 forçada em pleno uso (token expirado no meio de uma
sessão, não só no F5) aciona o retry automático via refresh e a tela
se recupera sem o usuário perceber. Zero erros de console/JS durante
todo o percurso.

### O que fica pra próxima leva (não é esquecimento, é sequenciamento)

Todo o resto da superfície do backend: gerenciar rede de confiança
(convidar, permissões, observações), medicações e rotina, histórico
de alertas e explicabilidade, plano pessoal (criar/editar/plano de
crise), configurações de conta (exportar/excluir dados, trocar
senha), consulta de auditoria, painel analítico, o painel restrito da
pessoa de confiança, e o modo "Quase vazio"/tema escuro mencionados
como opção de interface desde o início do projeto. Nenhuma dessas
telas tem lógica nova a inventar — é o mesmo padrão desta leva
(cliente de API + tela + verificação com Playwright), só que em
volume grande o bastante pra merecer sequenciar com o usuário antes
de sair construindo tudo de uma vez.

## 2026-09-12 — ETAPA 26: auditoria (consolidação + consulta)

### O que foi feito

Item 31 já vinha sendo parcialmente atendido desde a ETAPA 7:
`AuditLog` gravado em `invite_sent`, `permission_granted`/`_revoked`,
`external_observation_recorded`, `restricted_data_access_denied`
(ETAPA 7), `plan_changed` (ETAPA 25), `data_exported`/
`account_deletion_requested` (ETAPA 25). O trabalho real desta etapa
foi achar e fechar o que faltava — confirmado ao vivo via grep antes
de começar, mesmo padrão recorrente do projeto de enum "pré-modelado"
sem lógica em cima:

- **`AuditAction.LOGIN`** — existia desde o início do enum, nunca era
  gravado. Agora gravado em `auth_service.authenticate` em todo login
  bem-sucedido (com `ip_address`, quando disponível). Login FALHO
  deliberadamente NÃO gera linha: já tem seu próprio controle
  (`failed_login_attempts`/`locked_until`), e uma trilha de tentativas
  falhas exposta na consulta de auditoria seria, ela mesma, um vetor
  de informação sobre a conta.
- **`AuditAction.PASSWORD_CHANGE`** — gravado tanto em
  `change_password` quanto em `reset_password` (metadata `via`
  diferencia qual caminho foi usado, sem nunca guardar a senha em si,
  óbvio, mas também nunca nem o hash — item 54).
- **`AuditAction.CRITICAL_ALERT`** — gravado em
  `alert_service.sync_alert_state`, só na TRANSIÇÃO de verdade pra
  VERMELHO (nunca em toda reavaliação, mesma regra de "só quando muda"
  que já existia pra criar a linha em `Alert` alguns passos acima —
  testado explicitamente: chamar `/alerts/sync` de novo sem mudança
  real não duplica a auditoria).
- **`GET /audit-log?limit=&offset=`** — consulta paginada (item 65:
  nunca histórico ilimitado de uma vez; `limit` 1-200, padrão 50) do
  que aconteceu com a PRÓPRIA conta (`AuditLog.target_user_id`, nunca
  o que o usuário fez como pessoa de confiança de outra conta — isso
  pertence ao audit log da outra pessoa). Cada linha expõe `action`,
  `metadata` (já saneado por quem grava, nunca dado sensível — item
  54), `created_at` e `actor_is_self: bool` — nunca o id de quem foi o
  ator quando não é o próprio dono: a pessoa vê "uma pessoa de
  confiança fez X" sem saber qual delas só por esta rota; cruzar isso
  com a lista de relacionamentos pra identificar quem foi é decisão de
  UI, ETAPA 27 (frontend), não desta API que só lê.

### Decisão de escopo registrada: por que só `target_user_id`, nunca `actor_user_id`, na consulta

Um usuário só pode ver auditoria do que aconteceu À CONTA DELE. Se ele
também é pessoa de confiança de outra pessoa e registrou uma
observação lá, essa linha (`actor_user_id` = ele, `target_user_id` =
o dono da outra conta) não aparece na consulta dele — apareceria seria
na consulta da OUTRA pessoa. Simetria simples: cada um só vê o que foi
feito à própria conta, nunca o que fez à conta alheia (isso já é
visível de outro jeito — a própria resposta da ação que ele executou).

### Testes

205 testes (8 novos): gravação das três lacunas fechadas, não
duplicação de `CRITICAL_ALERT` numa reavaliação sem mudança, consulta
vazia/cronológica/paginada/isolada-entre-usuários, e o caso
`actor_is_self=False` quando quem gerou a linha foi uma pessoa de
confiança agindo sobre a conta observada. Smoke test manual via curl
confirmou login/troca de senha/transição pra vermelho gravando (e a
segunda chamada de `/alerts/sync` sem mudança real não duplicando).

---

## 2026-09-12 — ETAPA 25: configurações e privacidade (plano pessoal, exportação e exclusão de conta)

### O que foi feito

Três peças, as duas últimas amarrando um requisito de LGPD declarado
como escopo de v1 desde a ETAPA 1 (minimização, consentimento,
**exportação, exclusão**, auditoria):

- **Plano pessoal** (`PersonalPlan`/`PersonalPlanRule`, item 19 —
  "plano quando eu não perceber", estilo WRAP/Wellness Recovery Action
  Plan). Model já existia desde a ETAPA 4 sem nenhuma lógica em cima
  (confirmado ao vivo contra o Postgres via grep — zero uso em
  `app/`), mesmo padrão recorrente de peça "pré-modelada" que só ganha
  comportamento quando o documento de referência pede de fato.
  `POST/GET/PATCH /personal-plan`, `POST /personal-plan/deactivate`,
  `POST /personal-plan/rules`, `PATCH /personal-plan/rules/{id}`.
- **Acesso da pessoa de confiança ao plano** — `GET
  /trusted-people/{relationship_id}/personal-plan`, gated por
  `ACCESS_CRISIS_PLAN` (nível de permissão 5 do documento). Disponível
  a qualquer momento, não só num estado VERMELHO: o ponto de um plano
  estilo WRAP é a pessoa de apoio já conhecer o conteúdo ANTES de
  precisar dele.
- **Exportação de dados** (item 53) — `GET /account/export`, retrato
  síncrono em JSON (perfil, check-ins, histórico de rotina, eventos de
  vida, medicamentos, intervenções, plano pessoal, rede de confiança
  própria, notificações). Nunca inclui credencial nem e-mail/nome de
  outra pessoa. Gera `AuditLog` com `AuditAction.DATA_EXPORTED`.
- **Exclusão de conta** (item 53) — `POST /account/deactivate`,
  reconfirma senha (mesmo critério de `auth_service.change_password`),
  seta `User.deactivated_at`/`is_active=False` (campo modelado desde a
  ETAPA 4, checado em login/token desde a ETAPA 6, nunca setado em
  lugar nenhum até aqui) e revoga toda sessão (`revoke_all_sessions`).
  Gera `AuditLog` com `AuditAction.ACCOUNT_DELETION_REQUESTED`.

### Decisão de escopo registrada: exclusão é sempre soft delete

Apagamento físico após prazo de retenção legal fica de fora do MVP —
ainda não há prazo de retenção definido pelo usuário/produto, então um
job de expurgo automático seria inventar uma regra sem base. Decisão
explícita, não esquecimento, mesmo padrão já usado pra verificação de
e-mail (ETAPA 22). `get_current_user` já confere `is_active`/
`deactivated_at` contra o banco em toda requisição (nunca só o claim
do token) — confirmado ao vivo: o mesmo access token emitido antes de
desativar já responde 401 na primeira chamada seguinte, sem precisar
esperar expirar.

### Decisão de escopo registrada: plano pessoal tem no máximo um ativo, sem versionamento nem reativação

Diferente de `Baseline`/`Routine` (que têm motivo real pra guardar
versão anterior — reclassificar o passado), o plano é um documento
vivo que a pessoa edita (`PATCH`), não uma sequência histórica.
`create_plan` recusa (409) se já existir um ativo. `deactivate_plan`
não tem endpoint de reativação, de propósito: reativar um plano antigo
sem revisá-lo contraria o espírito de "escrito enquanto estável" — a
pessoa deveria reler e reescrever, não só destravar o texto de antes.

### Bug encontrado e corrigido pelo próprio teste da etapa: `deactivate_plan` não era idempotente

A primeira versão de `deactivate_plan` buscava o plano via
`get_active_plan` (filtra `is_active=True`) antes de desativá-lo — na
segunda chamada, o plano já desativado não é mais encontrado por essa
função, e a rota devolvia 404 em vez do 200 idempotente que a própria
docstring prometia (mesmo padrão de `discontinue_medication`/
`revoke_relationship`). Corrigido com `_get_latest_plan`, uma busca
que ignora `is_active` e pega o plano mais recente do usuário — usada
só em `deactivate_plan`; as demais operações (criar, editar, adicionar
regra) continuam exigindo um plano efetivamente ativo via
`get_active_plan`, porque não faz sentido editar ou anexar regra a um
plano já desativado. Achado escrevendo
`test_deactivate_plan_is_idempotent_and_allows_recreation` antes de
rodar a suíte — exatamente o motivo de nunca fechar uma ETAPA sem
teste cobrindo o caminho "chamar de novo".

### Testes

18 testes novos (`test_personal_plan.py`: 13 — CRUD do dono, unicidade
de plano ativo, isolamento entre usuários, idempotência real de
desativar, acesso da pessoa de confiança com/sem `ACCESS_CRISIS_PLAN`
e 404 quando o dono ainda não escreveu plano; `test_account.py`: 5 —
formato e conteúdo da exportação, auditoria de exportação e de
desativação, senha incorreta rejeitada, bloqueio de acesso e login
imediatamente após desativar). Suíte completa: **197 testes, 197
passando**. Smoke test manual confirmou ao vivo: criação/edição/
desativação/recriação de plano, gate 403→200 do plano de crise após
conceder a permissão, exportação com dado real, e o efeito completo de
desativar conta (export bloqueado, login bloqueado, tudo com o mesmo
token/senha usados antes).

---

## 2026-09-12 — ETAPA 23/24: dashboards (diário, analítico e da pessoa de confiança)

### O que foi feito

Três visões, todas montadas em cima do que as etapas anteriores já
calculam — nenhuma lógica nova de baseline/desvio/estado é criada
aqui, mesmo raciocínio já registrado em `explainability_service`
(ETAPA 20): dashboard organiza pra exibição, nunca recalcula.

- **`GET /dashboard/daily`** (ETAPA 23) — a visão "agora": estado
  atual (verde/amarelo/vermelho) e desde quando, check-in de hoje (se
  já foi feito), lista de doses de medicação esperadas hoje com o
  status de cada uma (`null` quando ainda não há registro), lista de
  intervenções em andamento (SUGGESTED/REQUESTED/ACCEPTED/STARTED —
  nunca as já FINISHED/DISMISSED), contagem de notificações não lidas
  e as 5 mais recentes.
- **`GET /dashboard/analytics?days=30`** (ETAPA 24) — a visão
  histórica: linha do tempo de mudança de estado, tendência por
  indicador (baseline vs. valor recente, de todo baseline ativo),
  linha do tempo de `DeviationEvent` por motor, taxa de adesão a
  medicação agregada no período (`null`, não zero, quando não havia
  dose agendada) e estatística de intervenções (contagem por status,
  quantas ajudaram/não ajudaram/sem avaliação ainda). `days` limitado
  entre 7 e 365 — item 65, não faz sentido nem um dia (isso já é o
  dashboard diário) nem "todo o histórico" sem paginação.
- **`GET /trusted-people/{relationship_id}/dashboard`** — a visão da
  PESSOA DE CONFIANÇA. Esta é a única das três que não mostra tudo:
  o documento de referência é explícito ("não mostraria histórico
  completo de humor... simplesmente porque alguém é pessoa de
  confiança"), então cada seção do corpo da resposta só é preenchida
  se a permissão correspondente estiver concedida NESTE
  relacionamento — sem a permissão, a seção inteira vem `null` (nunca
  uma lista vazia, que confundiria "sem permissão" com "sem dado"):
  - estado atual: só revela AMARELO/VERMELHO se a pessoa tiver
    `RECEIVE_ALERT_YELLOW`/`RECEIVE_ALERT_RED` especificamente pra
    aquele estado — VERDE nunca é sensível e sempre aparece. Mesmo par
    permissão/estado que `notification_service.notify_alert_state_change`
    já usa desde a ETAPA 22 (reusado, não reinventado).
  - adesão a medicação: `VIEW_MEDICATION` — só a taxa agregada dos
    últimos 30 dias, nunca dose a dose.
  - indicadores: `VIEW_SPECIFIC_INDICATORS` — só os liberados em
    `Permission.indicator_scope`, nunca todo baseline ativo do dono.
  - linha do tempo de estado e de desvio: `VIEW_FULL_HISTORY`.
  - pedidos de body doubling pendentes endereçados a ela:
    `HELP_WITH_TASK` (mesma permissão que já gate aceitar o pedido,
    ETAPA 21 — aqui só lista os que ainda esperam aceite).

  A rota em si não exige nenhuma permissão única pra responder — só
  que o relacionamento exista, pertença a quem está autenticado como
  pessoa de confiança, e esteja ativo (`authorization_service.
  get_active_relationship_for_trusted_user`, dependency nova
  `require_active_relationship` em `deps.py`, ao lado de
  `require_relationship_permission` já existente). Decisão registrada:
  isso é deliberadamente diferente do resto da ETAPA 7 (uma permissão
  obrigatória por rota) porque este é o primeiro endpoint que combina
  várias permissões *opcionais* — cada seção decide sozinha se aparece.

### Decisão de escopo registrada: "hoje" tem dois critérios diferentes no código, de propósito

O dashboard diário calcula "hoje" no fuso do `Profile` (mesmo critério
de `checkin_service._today_for_user`, duas linhas repetidas em vez de
importar uma função privada de outro módulo — não vale acoplar por
isso). Já o preenchimento automático de dose esquecida
(`scheduler_service`, ETAPA 22) sempre trabalhou em dia UTC. São dois
módulos com "hoje" calculado de jeitos diferentes — registrado aqui em
vez de "corrigido" por conta própria: unificar o critério do scheduler
é decisão de produto (muda quando uma dose vira `FORGOT_TO_CONFIRM`),
fora do escopo de um dashboard que só lê dado já existente.

### Verificação

179 testes (`pytest -q`, 20 novos em `test_dashboard.py`): dashboard
diário vazio vs. preenchido (check-in, dose de medicação com/sem
weekday de hoje, intervenção ativa vs. finalizada, contagem de não
lidas), dashboard analítico vazio vs. preenchido (baseline como
tendência, linha do tempo de alerta/desvio, adesão a medicação,
estatística de intervenção, limite de `days` 422 fora de [7,365]), e
nove cenários do dashboard da pessoa de confiança (relacionamento
ainda pendente → 404, relacionamento de outra pessoa → 404, VERDE sem
nenhuma permissão, AMARELO escondido/revelado, VERMELHO exige a
própria permissão — não a de AMARELO —, adesão/indicadores/histórico
completo/pedidos pendentes cada um gated pela permissão certa). Smoke
test manual via curl confirmou os três endpoints ao vivo, incluindo o
caso "pessoa de confiança sem nenhuma permissão concedida" devolvendo
todas as seções sensíveis como `null` e só o estado VERDE aparecendo.

Próximo passo: **ETAPA 25 — Configurações/privacidade** (provável
lugar pra `PersonalPlan`/`PersonalPlanRule`, item 19, ainda adiado).

---

## 2026-09-12 — ETAPA 22: notificações, ciclo noturno e e-mail de verdade

### O que foi feito

Os models `Notification`/`NotificationPreference` (item 37) e
`PersonalPlan`/`PersonalPlanRule` (item 19) já existiam desde a
ETAPA 4 — só `Notification`/`NotificationPreference` ganham
comportamento nesta etapa; `PersonalPlan` fica deliberadamente pra
depois (ver "escopo deixado de fora" abaixo).

- **`app/services/notification_service.py`**: motor de anti-spam do
  item 37. `create_notification` resolve o canal (`channel_by_type`
  por tipo, default `PUSH`), decide se entrega agora ou adia
  (`scheduled_for`) por horário silencioso (`quiet_hours_start/end`,
  atravessando meia-noite ou não) ou teto diário
  (`max_notifications_per_day`) — nunca descarta, só adia.
  Prioridade `HIGH` nunca é adiada nem contida pelo teto: reservada
  pro estado VERMELHO (item 20 — "protocolo de crise pré-definido"
  não pode ser silenciado por configuração de conveniência).
  `deliver_due_notifications` entrega o que ficou represado; canal
  `EMAIL` de fato envia (`app/core/email.py`), `PUSH`/`IN_APP` só
  vivem como linha no banco (nenhum provedor de push está conectado
  — precisaria de token de dispositivo, que não existe no modelo
  ainda).
- **`app/core/email.py`**: abstração de envio. Sem `SMTP_HOST`
  configurado (nenhuma variável de ambiente do projeto define isso),
  cai num backend de log — o "provedor ainda não conectado" citado
  desde a ETAPA 6 finalmente tem um lugar pra existir sem travar o
  produto. Configurar as variáveis `SMTP_*` liga o envio real via
  `smtplib` padrão do Python, sem mudar nenhum código de quem chama
  `send_email`.
- **Duas integrações de domínio que passam a notificar de verdade**:
  `alert_service.sync_alert_state` (só na transição de estado de
  verdade, nunca em reavaliação sem mudança) chama
  `notification_service.notify_alert_state_change` — dono é avisado
  sempre (inclusive alívio, voltar a VERDE), rede de confiança só em
  AMARELO/VERMELHO e só quem tem `RECEIVE_ALERT_YELLOW`/
  `RECEIVE_ALERT_RED` concedida (nenhuma permissão nova, as duas já
  modeladas desde a ETAPA 7 finalmente em uso). `intervention_service.request_intervention`
  notifica a pessoa de confiança específica endereçada
  (`support_relationship_id`) quando um pedido de body doubling é
  feito — nunca a rede inteira.
- **`app/services/scheduler_service.py`** (lógica testável) +
  **`app/core/scheduler.py`** (fiação do APScheduler, nunca testada
  por unidade — mesma separação de `app/api` vs `app/services`):
  `run_nightly_cycle` roda, por usuário ativo,
  `fill_forgotten_medication_events` (preenche `FORGOT_TO_CONFIRM`
  pra dose agendada há mais de 3h sem nenhum registro — nunca antes
  de o próprio horário existir, nunca mais que 3 dias pra trás) e o
  que já existia manualmente por trás de `POST /deviation/run*` +
  `POST /alerts/sync`. Erro num usuário nunca derruba o ciclo dos
  outros: cada um roda no próprio try/except com rollback isolado
  (usuário recarregado por id a cada iteração — nunca reusa o objeto
  ORM de antes de um rollback anterior, ver bug de teste abaixo).
  `app/main.py` liga isso via `lifespan` do FastAPI: ciclo noturno às
  3h UTC, entrega de notificações represadas a cada 15 minutos.
- **E-mail de reset de senha finalmente sai de verdade**:
  `auth_service.create_password_reset_token` agora chama
  `email.send_email` com o link de reset — antes disso o token só
  existia no banco, sem nenhum jeito de a pessoa recebê-lo fora de um
  teste.

### Escopo deixado de fora (decisão explícita)

- **Verificação de e-mail no cadastro**: `docs/decisions.md`
  registrava desde a ETAPA 6 que isso seria "resolvido junto" nesta
  etapa — decisão revista aqui: exigiria um novo modelo (token de
  verificação) e uma coluna nova em `User`, é uma feature de
  autenticação por si só, não uma consequência natural de ligar
  notificação/e-mail. Adiado pra não inflar esta etapa sem
  necessidade (item 65).
- **`PersonalPlan`/`PersonalPlanRule`** (item 19, "Plano quando eu
  não perceber"): fica pra uma etapa própria. É conceitualmente
  diferente do motor de estado (ETAPA 19: convergência entre
  motores, sem julgamento clínico) — é a própria pessoa pré-
  autorizando, em período estável, que padrões específicos importem
  mais que o autorrelato dela no momento ("você definiu antes que
  isso deveria gerar atenção"). Merece a mesma atenção dedicada que
  o modelo de estado teve, não um apêndice da etapa de notificações.
- Nenhum provedor de push de verdade (item já registrado acima).

### Bug de infraestrutura de teste encontrado e corrigido

Escrevendo `test_scheduler_service.py` (o primeiro teste da suíte
inteira a chamar `session.rollback()` explicitamente, e não só
`db.commit()`), um `session.rollback()` no meio do teste passou a
reverter a transação EXTERNA inteira (apagando até usuário já
"commitado" antes), não só a savepoint atual — o listener em
`tests/conftest.py` usava a condição documentada pro SQLAlchemy 1.x
(`transaction.nested and not transaction._parent.nested`), que para
de disparar depois de alguns ciclos de commit/reabertura de
savepoint. Corrigido trocando pela condição recomendada pelos
próprios docs do SQLAlchemy 2.0 pro mesmo padrão:
`connection.in_nested_transaction()` (estado da conexão, não do
objeto `SessionTransaction` do ORM). Reproduzido isoladamente antes
da correção (um `session.rollback()` sozinho, depois de um único
`register_and_login`, já apagava o usuário) e confirmado depois:
suíte inteira (130 testes até então) continuou passando sem nenhuma
mudança de comportamento — o bug só afetava quem chamasse
`rollback()` explicitamente, o que nenhum teste fazia antes desta
etapa.

### Verificação

- 29 testes novos: `tests/test_notifications.py` (20 — anti-spam:
  horário silencioso atravessando meia-noite, teto diário, `HIGH`
  nunca contido, entrega adiada, canal por tipo enviando e-mail de
  verdade via mock; listagem/leitura idempotente e privada;
  integração com `Alert` — amarelo avisa o dono, vermelho avisa a
  rede com a permissão certa e só ela, permissão de vermelho não
  vaza pra amarelo, reavaliação sem mudança não duplica; integração
  com body doubling — pedido endereçado notifica só quem foi
  chamado, microintervenção sem relacionamento não notifica ninguém;
  reset de senha envia e-mail com o link, e-mail inexistente não
  envia nada) e `tests/test_scheduler_service.py` (9 — preenchimento
  de dose esquecida após o grace period, nada dentro do grace period,
  sem duplicar evento existente, respeita dias da semana, nunca
  preenche antes de o horário existir, alimenta o indicador de
  adesão, ciclo noturno sincroniza alerta sem endpoint manual nenhum,
  isola falha de um usuário do outro, wrapper de entrega delega
  certo).
- `pytest -q` → **159 passed** (130 anteriores + 29 novos).
- Smoke test manual via `curl` contra o servidor real: preferências
  default e PATCH parcial; forçar duas convergências de motor
  (evitação + estabilidade) via check-ins reais → `POST
  /alerts/sync` → VERMELHO → notificação `HIGH` criada pro dono E
  pra pessoa de confiança com `RECEIVE_ALERT_RED` concedida, cada
  uma com o `relationship_id` certo no payload; marcar notificação
  como lida e confirmar que some da listagem `unread_only`; `POST
  /auth/password-reset/request` confirmado gerando e enviando (log)
  o e-mail com o link funcional; scheduler confirmado subindo e
  descendo de verdade via o `lifespan` do FastAPI (2 jobs
  registrados: ciclo noturno às 3h UTC, entrega a cada 15min) — o
  próprio processo `uvicorn` também precisou ser reiniciado com um
  procedimento adicional de log (nível WARNING em vez de INFO nos
  dois logs de confirmação — `logging` do Python filtra INFO por
  padrão, um log que ninguém vê no console não serve nem como
  fallback de desenvolvimento).

Próximo passo: **ETAPA 23/24 — Dashboards** (painel de baseline,
estado atual e histórico de intervenções pro próprio usuário).

---

## 2026-09-12 — ETAPA 21: intervenções (microintervenção / body doubling)

### O que foi feito

`app/services/intervention_service.py` + `app/api/v1/intervention.py`
+ uma rota nova em `trusted_people.py`. Os models (`Intervention`,
`InterventionResult`) já existiam desde a ETAPA 4 — conferido ao vivo
contra o Postgres antes de começar (30 tabelas já existentes) — então
esta etapa não tem migration nova, só comportamento.

- **`POST /interventions/suggest`** cria uma intervenção em
  `SUGGESTED`. Tipo default `MICROINTERVENTION` (menor atrito
  primeiro, item 24); `BODY_DOUBLING_SESSION` explícito quando quer
  pular direto pra esse degrau. `related_task_id`/`related_deviation_id`
  são validados como pertencentes ao próprio usuário reusando
  `task_service.get_task`/`deviation_service.get_deviation_event` — 404
  se não forem (mesmo padrão "404 não 403" do resto do projeto).
- **Catálogo de microintervenções**: 5 textos fixos em português
  (reduzir ao menor passo, timer de 5 minutos, contato social breve,
  retomar rotina mínima, preparar o ambiente antes de decidir) —
  rotacionados de forma **determinística** (conta quantas
  microintervenções aquele usuário já recebeu, `% len(catálogo)`) em
  vez de aleatório, pra ficar testável sem mockar sorteio. Body
  doubling tem um texto fixo só (pedir pra alguém ficar por perto).
- **Máquina de estados** (`SUGGESTED → REQUESTED → ACCEPTED → STARTED
  → FINISHED`, `DISMISSED` a qualquer momento não-terminal) —
  diferente de `Task`, sem tabela de evento própria (decisão de
  escopo abaixo). `start` aceita partir de `SUGGESTED`, `REQUESTED`
  **ou** `ACCEPTED`: item 17 do documento (escada de escalonamento —
  reduzir → timer → body doubling → começar) exige atrito mínimo, e a
  própria intervenção pensada pra ajudar a não procrastinar pode ser
  procrastinada. Uma microintervenção normalmente pula direto de
  `SUGGESTED` pra `STARTED` (não tem outra parte envolvida pra
  "pedir"/"aceitar"); body doubling tipicamente segue a escada
  inteira, mas nada impede o atalho se a pessoa já topou por fora do
  app.
- **Body doubling de ponta a ponta**: `POST /interventions/{id}/request`
  com `support_relationship_id` opcional marca a quem o pedido foi
  endereçado (validado como relacionamento do próprio dono via
  `trust_service.get_relationship_for_owner` — que virou pública
  nesta etapa, antes era `_get_relationship_for_owner`). A pessoa de
  confiança aceita em
  **`POST /trusted-people/{relationship_id}/interventions/{intervention_id}/accept`**,
  gated por `require_relationship_permission(PermissionKey.HELP_WITH_TASK)`
  — primeiro uso real dessa permissão, registrada como "sem uso por
  ora" na decisão da ETAPA 10. A busca dentro do service filtra
  também por `support_relationship_id == relationship.id`: ter
  `HELP_WITH_TASK` concedida não dá acesso a aceitar qualquer pedido
  de qualquer pessoa, só o que foi endereçado especificamente a essa
  pessoa (pedido endereçado a outra pessoa de confiança, ou nunca
  pedido a ninguém, devolve 404 — não revela nada sobre a existência
  do pedido).
- **`PUT /interventions/{id}/result`** só é aceito com a intervenção
  em `FINISHED` — "ajudou ou não" (item 24/26) é avaliado sobre algo
  que de fato aconteceu. Upsert: chamar de novo atualiza o mesmo
  `InterventionResult` (a pessoa pode reavaliar depois), nunca
  duplica — a coluna `intervention_id` já é `unique` no banco.

### Decisões de escopo registradas

- **Sem tabela de evento pra `Intervention`** (diferente de
  `Task`/`Routine`/`Alert`): o documento não pede histórico auditável
  rico por intervenção, só "ajudou ou não" — isso já mora em
  `InterventionResult`. `status` + `updated_at` (de `TimestampMixin`)
  bastam pra reconstruir quando cada transição aconteceu. Um
  `InterventionEvent` fica fácil de acrescentar depois, sem reescrever
  o módulo, se algum dia for preciso medir quanto tempo um pedido
  ficou parado em `REQUESTED`.
- **`request_intervention` não checa `HELP_WITH_TASK`** — só quem
  aceita precisa ter a permissão concedida. Pedir apoio não deveria
  depender de a outra pessoa já ter sido autorizada antes (a pessoa
  pode nem saber que vai ser chamada); a permissão importa no momento
  em que ela age, não no momento em que é convidada a agir.
- `trust_service._get_relationship_for_owner` virou pública
  (`get_relationship_for_owner`) especificamente pra ser reusada por
  este módulo — 4 usos agora (3 dentro de `trust_service` + 1 aqui),
  sem duplicar a query de "relacionamento pertence a este dono".

### Verificação

- 14 testes novos (`tests/test_interventions.py`): rotação do
  catálogo de microintervenções; texto fixo de body doubling; posse
  de tarefa/evento de desvio relacionados (404 pra quem não é dono,
  404 pra id inexistente); atalho de baixo atrito
  `SUGGESTED → STARTED`; transição inválida devolve 409; `dismiss` a
  partir de qualquer estado não-terminal (e não de novo depois de já
  dispensada); `record_result` rejeitado antes de `FINISHED` (409) e
  aceito depois; upsert de resultado sem duplicar; fluxo completo de
  body doubling com convite → aceite → permissão → pedido → aceite da
  pessoa de confiança → início → fim → resultado; aceitar sem a
  permissão é 403; aceitar um pedido endereçado a outro relacionamento
  é 404 mesmo com a permissão concedida; intervenções privadas ao
  dono; filtro por status na listagem.
- `pytest -q` → **130 passed** (116 anteriores + 14 novos).
- Smoke test manual via `curl` contra o servidor real (depois de
  encontrar e derrubar um `uvicorn` remanescente de uma sessão
  anterior, ainda de pé na porta 8000 com o código antigo, sem as
  rotas novas — resolvido com o mesmo procedimento já registrado de
  achar o PID pelo inode do socket em `/proc/net/tcp`): sugerir
  3 microintervenções seguidas confirmou a rotação do catálogo linha
  por linha; fluxo completo de body doubling (convite, aceite,
  concessão de `HELP_WITH_TASK`, pedido endereçado, aceite da pessoa
  de confiança, início, fim) bateu exatamente com os testes
  automatizados; tentar aceitar um pedido nunca endereçado àquele
  relacionamento devolveu 404; transição inválida (`finish` a partir
  de `SUGGESTED`) devolveu 409.

Próximo passo: **ETAPA 22 — Notificações** (é ali que `POST
/interventions/suggest` deixa de ser só manual e passa a ser
disparado automaticamente a partir de `DeviationEvent`/`Alert`, junto
do job noturno que também finalmente resolve o `FORGOT_TO_CONFIRM`
automático de medicação e o envio de e-mail de reset de senha).

---

## 2026-09-12 — Revisão geral (bug + repetição), pedida explicitamente pelo usuário

Antes de seguir pra ETAPA 21, parada pra auditar tudo que foi
construído até aqui (ETAPA 1-20): procurar bug real, código
repetido, e qualquer coisa otimizável. Achados e correções:

### Bug real: PATCH de check-in limpando um campo deixava indicador obsoleto

`checkin_service.update_checkin` sempre chamava
`indicator_service.sync_checkin_indicators`, mas essa função só
escrevia (`_upsert_indicator`) quando o campo tinha valor — um
`PATCH /checkins/{data}` com `{"mood": null}` (depois de `mood` já
ter sido enviado antes) zerava `DailyCheckIn.mood` no banco, mas o
`FunctionalIndicator` de `mood` daquele dia continuava com o valor
antigo intacto. "Sem dado" virava, silenciosamente, "o último dado
que existiu" — e baseline/motor de desvio liam esse valor obsoleto
como se ainda fosse real. Nenhum teste cobria esse caminho (todos os
testes de PATCH só trocavam um valor por outro, nunca por `null`).

Corrigido em `indicator_service.sync_checkin_indicators`: campo que
volta a `None` agora apaga (`_delete_indicator_if_exists`) o
`FunctionalIndicator` daquele dia/fonte em vez de deixá-lo parado.
Teste de regressão adicionado em `test_baseline.py`
(`test_checkin_patch_clearing_a_field_deletes_the_stale_indicator`) e
confirmado também via curl contra servidor real.

### Repetição: `_register_and_login`/`_user_id`/`_post_checkin` duplicados em 10 arquivos de teste

Helper idêntico, palavra por palavra, redefinido em `test_alerts.py`,
`test_baseline.py`, `test_checkins.py`, `test_deviation.py`,
`test_explainability.py`, `test_medications.py`, `test_profile.py`,
`test_routines.py`, `test_tasks.py` e `test_trusted_people.py` (mais
`_user_id`/`_post_checkin` duplicados em 2-3 arquivos cada). Movidos
pra `tests/conftest.py` (`register_and_login`, `user_id`,
`post_checkin`) e reimportados em cada arquivo — em alguns
(`test_deviation.py`, `test_explainability.py`) importados com alias
pro nome antigo (`as _register_and_login`) pra não precisar tocar em
cada chamada já escrita.

### Repetição: `def _now(): return datetime.now(timezone.utc)` duplicado em 6 services, mais 15+ chamadas inline do mesmo padrão espalhadas em mais 6 arquivos

`task_service`, `routine_service`, `medication_service`,
`baseline_service`, `deviation_service` e `alert_service` tinham,
cada um, a mesma função `_now()` copiada e colada. `auth_service`
(8x), `trust_service` (5x), `authorization_service`,
`indicator_service`, `profile_service` e `app/core/security.py`
chamavam `datetime.now(timezone.utc)` inline repetidamente. Nenhum
bug (todos faziam a coisa certa), mas dado que o próprio `Alert` já
tinha revelado um problema real de confiar em timestamp sem cuidado
(ETAPA 19 — `now()` do Postgres por transação), centralizar isso
numa única função reduz a chance de alguém, no futuro, reintroduzir
uma variação sutil (fuso errado, `datetime.utcnow()` sem tzinfo,
etc.) em só um dos vários lugares.

Criado `app/core/time.py` com um único `utc_now()`. Cada service que
tinha `_now()` local agora importa
`from app.core.time import utc_now as _now` (nenhuma chamada
existente precisou mudar de nome); os arquivos com chamada inline
importam `utc_now` direto. `checkin_service._today_for_user` foi
deixado como está — usa fuso dinâmico do perfil, não é o mesmo
padrão.

### Verificação

116 testes passando (`pytest -q`, sem nenhuma falha durante o
refactor — a suíte funcionou como rede de segurança pra confirmar que
mover código nunca mudou comportamento). Servidor reiniciado do zero
e testado manualmente ponta a ponta: fluxo completo de auth
(login → refresh → logout, que passa pelas 8 chamadas reescritas em
`auth_service`) e o bug do check-in reproduzido e confirmado corrigido
via curl.

---

## 2026-09-12 — ETAPA 20: explicabilidade

### O que foi construído

`app/services/labels.py` (novo, extraído de dentro de
`deviation_service`/`alert_service` — os rótulos em português de
motor/indicador viviam duplicados nos dois módulos; agora é uma
única fonte). `app/schemas/explainability.py` com
`IndicatorExplanation`/`EngineExplanation`/`AlertExplanation`, cada
um com um `classmethod` que só reorganiza dado já existente (mesmo
padrão de `BaselinePublic.from_baseline` na ETAPA 17), e
`app/services/explainability_service.py`, uma casca fina que busca o
`DeviationEvent`/`Alert` (reusando `deviation_service`/
`alert_service`, nunca duplicando a lógica de ownership) e chama o
`classmethod` certo. Duas rotas novas, penduradas nos routers já
existentes (nenhum router novo, nenhuma mudança em `main.py`): `GET
/deviation/events/{id}/explanation` e `GET
/alerts/{id}/explanation`. `tests/test_explainability.py`, 6 testes
novos — suíte foi de 109 para **115 testes**.

### Por que "explicabilidade" aqui não calcula nada

Item 15 do documento ("descobrir o gargalo": ao detectar uma mudança,
perguntar o que aconteceu, não só apontar o dedo) e item 22 (nenhum
alerta sem explicação) já estavam parcialmente atendidos desde a
ETAPA 18 (`DeviationEvent.explanation`/`baseline_snapshot`) e ETAPA
19 (`Alert.reason_summary`). O que faltava era **navegabilidade**: o
`baseline_snapshot` é um JSON bruto, útil pra máquina, não pra
interface. Esta etapa só decompõe esse JSON num formato estruturado
por indicador (rótulo em português, baseline vs. valor recente,
direção "acima/abaixo do seu padrão habitual", quantos dias
seguidos) e agrega por `Alert` quantos motores convergiram de quantos
possíveis (`breadth_score`) — sem nunca reabrir baseline, recalcular
z-score ou reavaliar estado. Reaproveitar em vez de recalcular é o
que garante que a explicação e o estado nunca divirjam entre si.

### Decisão de escopo: explicação de `Alert` é sempre "ao vivo", não retroativa exata

`Alert` guarda só um `DeviationEvent` representante
(`triggering_deviation_id`), não a lista completa de motores que
convergiam no instante exato daquela transição. `explain_alert`
recalcula essa lista a partir de `alert_service.
list_active_deviation_events` (a mesma função que `sync_alert_state`
usa) — ou seja, a explicação de um `Alert` antigo reflete os
`DeviationEvent`s que ainda estão dentro da janela de relevância
**agora**, não um retrato congelado de quando ele foi criado. Pra um
histórico exatamente auditável por transição seria preciso guardar a
lista completa de eventos convergentes em cada `Alert` — decisão
consciente de não fazer isso ainda, revisitar quando o caso de uso
pedir de verdade.

### Verificação

115 testes passando (`pytest -q`). Smoke test manual: humor e energia
caindo juntos gerando `red`, e `/alerts/{id}/explanation` devolvendo
os dois motores (`stability`, `activation`) cada um com seu indicador
decomposto (`mood`/`energy`, média do baseline, valor recente,
direção, dias seguidos) — nada recalculado, só o que já existia em
`DeviationEvent` reorganizado.

---

## 2026-09-12 — ETAPA 19: modelo de estado (Alert verde/amarelo/vermelho)

### O que foi construído

`app/services/alert_service.py` — lê os `DeviationEvent`s recentes
(últimos `RECENT_WINDOW_DAYS = 7` dias) dos 4 motores da ETAPA 18 e
decide o estado atual. `app/schemas/alert.py` e `app/api/v1/alerts.py`:
`POST /alerts/sync` (reavalia e só grava linha nova se o estado
mudou), `GET /alerts/current` (404 antes do primeiro sync), `GET
/alerts` (histórico completo), `POST /alerts/{id}/acknowledge` e
`POST /alerts/{id}/resolve` (ambos idempotentes). `main.py` ganhou o
router. `tests/test_alerts.py`, 10 testes novos — suíte foi de 99
para **109 testes**.

### Regra de estado (por que não inventei limiar clínico)

O documento de referência é explícito (item 20): regras transparentes
e configuráveis, nunca limiar clínico inventado. E o próprio VERMELHO
que ele descreve inclui coisas que nenhum dado comportamental deste
sistema consegue inferir sozinho (ideação suicida, sintomas
psicóticos/maníacos) — isso é para o `PersonalPlanSignal`/plano de
crise que o próprio usuário define enquanto está estável (item 19,
ainda não implementado), nunca para este motor declarar por conta
própria. O que os dados hoje sustentam de forma defensável é
justamente o critério do item 14: "faça isso simultaneamente em
vários domínios e aparece algo muito mais interessante". Por isso:

- **VERDE**: nenhum `DeviationEvent` de nenhum motor dentro da janela
  de 7 dias.
- **AMARELO**: exatamente um motor com desvio persistente recente —
  corresponde à descrição do documento de "deterioração": um padrão
  já existe, não é só "preguiça".
- **VERMELHO**: `RED_MIN_ENGINES = 2` ou mais motores convergindo ao
  mesmo tempo — "vários domínios ao mesmo tempo", nunca um julgamento
  de gravidade clínica.

Ambas as constantes (`RECENT_WINDOW_DAYS`, `RED_MIN_ENGINES`) são
simples, nomeadas, e comentadas — o objetivo declarado no item 20 é
poder mudar essas regras sem reescrever o motor, exatamente como
`Z_THRESHOLD`/`MIN_DURATION_DAYS` na ETAPA 18.

### Nunca sobrescreve o estado — sempre uma linha nova na transição

Mesmo padrão já usado em `TaskEvent`/`RoutineEvent`: `Alert` é um log
de transições, o estado "atual" é sempre a linha mais recente
(`get_current_alert`). Reavaliar sem mudança de estado (`POST
/alerts/sync` chamado várias vezes seguidas com os mesmos dados) não
grava nada novo — evita poluir o histórico de reconstrução da linha
do tempo (item 27).

### Bug de teste encontrado e corrigido: `now()` do Postgres é por transação, não por statement

Primeira rodada de testes revelou uma pegadinha real: `Alert` usa
`TimestampMixin` (`created_at` com `server_default=func.now()`).
Dentro da mesma transação SQL — que é exatamente como o fixture de
teste roda cada teste (uma transação externa nunca commitada, com
SAVEPOINTs por dentro) — `now()` do Postgres fica **congelado no
início da transação**, então dois `Alert`s criados no mesmo teste
tinham `created_at` idêntico e a ordenação por "mais recente primeiro"
ficava indeterminada. Corrigido setando `created_at` explicitamente
em Python (`datetime.now(timezone.utc)`) na criação do `Alert`, o
mesmo padrão que `DeviationEvent.detected_at`/`BaselineMetric.
computed_at` já usavam — nunca depender de `server_default` quando a
ordem entre linhas importa.

### Fora de escopo aqui, de propósito

Notificar a rede de confiança quando o estado muda
(`RECEIVE_ALERT_YELLOW`/`RECEIVE_ALERT_RED`, permissões já modeladas
desde a ETAPA 7) é a ETAPA 22, quando o canal de notificação e o job
noturno existirem de verdade — por ora tanto `POST /deviation/run`
quanto `POST /alerts/sync` são disparados manualmente.

### Verificação

109 testes passando (`pytest -q`). Smoke test manual: humor e energia
caindo juntos por 3 dias disparou os motores Estabilidade e Ativação
simultaneamente, e `/alerts/sync` corretamente devolveu `red` com
`reason_summary` listando as duas áreas.

---

## 2026-09-12 — ETAPA 18: motor de desvio (Executivo/Evitação/Ativação/Estabilidade)

### O que foi construído

`app/services/deviation_service.py` — o motor que lê `Baseline`/
`BaselineMetric`/`FunctionalIndicator` (nunca dado bruto) e decide,
por motor, se há desvio persistente o bastante pra virar um
`DeviationEvent`. `app/schemas/deviation.py` (schema de leitura) e
`app/api/v1/deviation.py`: `POST /deviation/run` (roda os 4 motores),
`POST /deviation/run/{engine}` (roda um só), `GET /deviation/events`
(com filtro por `engine`), `GET /deviation/events/{id}`. `main.py`
ganhou o router. `tests/test_deviation.py`, 10 testes novos — suíte
foi de 89 para **99 testes**, todos passando de primeira.

### Mapeamento motor → indicador (decisão de escopo)

O documento de referência descreve cada motor com uma lista mais rica
de sinais (sono, saída de casa, contato social, carga de evitação
etc.) do que o que hoje tem fonte de dado real (ver decisão já
registrada na ETAPA 17 sobre quais `IndicatorKey` têm ingestão). Como
o motor só conhece `FunctionalIndicator` — nunca a origem — mapear
cada motor pros indicadores que existem de verdade hoje, e ampliar
depois só acrescentando uma linha em `ENGINE_INDICATORS`, é a mesma
lógica de "trocar o motor analítico sem reescrever o resto" do item
38:

- **Executivo**: tarefas iniciadas (queda=ruim), tarefas concluídas
  (queda=ruim), tarefas adiadas (alta=ruim), capacidade percebida de
  começar tarefas (queda=ruim).
- **Evitação**: ansiedade (alta=ruim) — proxy de "preocupação
  antecipatória" até existir indicador dedicado (`AVOIDANCE_LOAD`,
  sem fonte real ainda).
- **Ativação**: energia (queda=ruim) — proxy até `LEFT_HOME`/
  `SOCIAL_CONTACT`/`ACTIVITY_LEVEL` terem fonte real.
- **Estabilidade**: adesão a medicação (queda=ruim), humor
  (queda=ruim).

### Algoritmo de detecção

1. **Amostra mínima de baseline** (`MIN_BASELINE_SAMPLE = 5`):
   indicador com menos de 5 dias de dado no baseline não participa —
   item 20 ("nunca inventar limiar clínico") não significa "decidir
   com qualquer quantidade de dado".
2. **Z-score direcionado**: `z = (valor - média) / desvio_padrão`,
   multiplicado por `+1` (subir é ruim) ou `-1` (descer é ruim) —
   `z_bad` positivo sempre significa "esse dia foi ruim nessa
   direção". `Z_THRESHOLD = 1.5`. Sem variabilidade (`stddev` None ou
   0) o indicador é ignorado nesse ciclo — nunca tratado como "sem
   desvio" nem como "desvio infinito".
3. **Persistência** (`MIN_DURATION_DAYS = 3`, item 1: nunca por dia
   isolado): anda dia a dia pra trás a partir do dia mais recente com
   dado, contando quantos dias seguidos `z_bad >= Z_THRESHOLD`.
   Indicador de **contagem** (tarefas) trata dia sem
   `FunctionalIndicator` como **zero de verdade** (ausência de evento
   de tarefa é zero atividade, de fato); indicador **subjetivo/
   adesão** trata dia sem registro como **buraco que quebra a
   sequência** (não dá pra supor o valor de um check-in que a pessoa
   não fez). Testado explicitamente nos dois sentidos em
   `test_deviation.py`.
4. Só cria `DeviationEvent` se pelo menos um indicador convergiu
   (`domains_count > 0`) — motores com um único indicador mapeado
   hoje (Evitação, Ativação) precisam poder disparar sozinhos;
   `convergence_score = domains_count / total_avaliado` já fica
   pronto pra distinguir "sinal isolado" de "vários juntos" assim que
   um segundo sinal real existir pra esses motores, sem mexer no
   motor de detecção.
5. `explanation` é gerada por template em português simples ("sua
   rotina mudou: ...") — item 22 (nenhum alerta sem explicação) e a
   diretriz de tom já registrada (nunca linguagem clínica/diagnóstica
   tipo "você está entrando em depressão").

### Fora de escopo aqui, de propósito

Este serviço produz só `DeviationEvent`, por motor. A leitura
combinada dos quatro motores que decide o estado verde/amarelo/
vermelho do usuário (`Alert`, item 20) é a **ETAPA 19**, mantendo o
mesmo padrão já usado entre `recompute`/`recalibrate` em
`baseline_service`: cada operação faz uma coisa só. `run_engine`
chama `baseline_service.recompute_baseline` pra cada indicador
mapeado antes de avaliar — ainda não existe job noturno (ETAPA 22),
então rodar o motor é hoje o que também mantém o baseline em dia.

### Verificação

99 testes passando (`pytest -q`). Smoke test manual contra servidor
real: 10 dias de humor estável (valor 4) seguidos de 3 dias de queda
(valor 1) — API devolveu `mean=3.3077`, `stddev=1.3156`,
`magnitude=1.7541`, `duration_days=3`, batendo exatamente com o
cálculo feito à mão em Python antes da chamada.

---

## 2026-09-11 — ETAPA 1 e 2: requisitos, ambiguidades e arquitetura

### Requisitos reescritos (forma técnica)

O documento de referência ("prompt-mestre") define um sistema que:
1. mantém um **baseline individual** por usuário, multi-variável
   (sono, atividade, tarefas, humor, adesão a medicação etc.);
2. detecta **desvio persistente** desse baseline, separado por 4
   "motores" (Executivo, Evitação, Ativação, Estabilidade), nunca por
   dia isolado;
3. permite uma **rede de confiança** com permissões granulares,
   revogáveis, testadas no backend;
4. nunca diagnostica, nunca prescreve, nunca decide sozinho sobre
   crise;
5. é auditável, exportável, excluível e minimiza dados sensíveis por
   design;
6. começa com regras transparentes e configuráveis (não IA opaca) e
   só evolui para IA como camada auxiliar depois de validado.

### Ambiguidades encontradas e como foram resolvidas

| Ambiguidade | Decisão | Por quê |
|---|---|---|
| Nome do produto — o documento usa "Sistema de Deterioração Funcional Pessoal" | Mantido **"Gancho"** como nome de trabalho (já usado nas automações e no painel existentes do projeto) | é o nome que já existe no projeto; o nome do documento é clínico e alarmista, contradiz a decisão de tom já tomada ("Companheiro calmo", sem infantilizar nem patologizar) |
| Trilha B estava "travada até Trilha A ter baseline real" — pedido atual parece iniciar Trilha B | **Construir a base do sistema agora é compatível com o gate**: o gate era sobre *lançar/usar* Trilha B com outras pessoas, não sobre escrever código. O motor de baseline é o mesmo para 1 ou N usuários — construir agora não antecipa o lançamento para terceiros | evita bloquear engenharia por uma trava que é sobre operação, não sobre arquitetura — mas o lançamento efetivo para pessoas fora do próprio usuário continua condicionado aos dados reais da Trilha A, como já decidido |
| Onde hospedar em produção | Em aberto — não decidido agora | requer conta/credencial (Railway, Fly.io, Render, Neon...) que não existe neste ambiente; a aplicação foi estruturada (Docker, variáveis de ambiente, Postgres padrão) para não exigir mudança de código quando isso for decidido |
| App nativo (push nativo, sensores de celular) | Fora do MVP | nenhum requisito do documento depende de sensor de hardware; PWA + Web Push cobre a hipótese principal com uma fração do custo de manter apps nativos |
| Fila de jobs (Celery/Redis) vs scheduler simples | Scheduler simples (APScheduler) embutido no worker | volume esperado no MVP não justifica a complexidade operacional extra; documento explicitamente pede para evitar overengineering (item 65) |
| Compliance LGPD | Tratado como requisito de v1 (minimização, criptografia, consentimento, exportação, exclusão, auditoria), não de "depois" | dado de saúde/comportamento é dado sensível sob a LGPD (art. 5º, II); usuário está no Brasil |

### Arquitetura e stack

Ver `architecture.md`. Resumo da stack: **FastAPI (Python) + PostgreSQL
+ SQLAlchemy/Alembic + JWT próprio + React/TypeScript/Vite (PWA)**.

### Ordem de implementação (adaptada das 36 etapas do documento de referência)

| # | Etapa | Status |
|---|---|---|
| 1 | Requisitos técnicos e ambiguidades | ✅ feito (este documento) |
| 2 | Arquitetura e stack definidas e justificadas | ✅ feito (`architecture.md`) |
| 3 | Estrutura do projeto, banco conectado, 1º teste verde | ✅ feito |
| 4 | Modelo de dados completo | ✅ feito |
| 5 | Migrations iniciais | ✅ feito (junto com a ETAPA 4, ver nota abaixo) |
| 6 | Autenticação | ✅ feito |
| 7 | Autorização (permissões) | ✅ feito (junto com 14 e 16, ver nota abaixo) |
| 8 | Usuários e perfil | ✅ feito (junto com 9, ver nota abaixo) |
| 9 | Onboarding | ✅ feito (junto com 8) |
| 10 | Tarefas e eventos de tarefa | ✅ feito |
| 11 | Check-ins | ✅ feito |
| 12 | Rotinas | ✅ feito |
| 13 | Medicamentos e adesão | ✅ feito |
| 14 | Pessoas de confiança | ✅ feito (junto com 7 e 16) |
| 15 | Sistema de permissões (UI + regra) | ✅ feito (junto com 7 e 14 — a "regra"; UI é ETAPA 27) |
| 16 | Observações externas | ✅ feito (junto com 7 e 14) |
| 17 | Baseline | ✅ feito |
| 18 | Motor de desvio | ✅ feito |
| 19 | Estados (Verde/Amarelo/Vermelho) | ✅ feito |
| 20 | Explicabilidade | ✅ feito |
| 21 | Intervenções | ✅ feito |
| 22 | Notificações | ✅ feito |
| 23 | Dashboard diário | ✅ feito (junto com 24, ver nota abaixo) |
| 24 | Dashboard analítico | ✅ feito |
| 25 | Configurações / privacidade | ✅ feito (plano pessoal, export e exclusão de conta — ver nota abaixo) |
| 26 | Auditoria | ✅ feito (login/troca de senha/alerta crítico gravados, consulta paginada da própria conta) |
| 27 | Frontend conectado ao backend | 🟡 primeira leva feita (auth + painel diário + check-in, verificado com Playwright); resto das telas em sequência |
| 28 | Estados de loading/erro/vazio/offline | ⬜ |
| 29 | Testes (cobertura ampla) | ⬜ |
| 30-32 | Revisão de segurança, UX, performance | ⬜ |
| 33-34 | Testes completos, correção de bugs | ⬜ |
| 35 | Ambiente de produção | ⬜ |
| 36 | Documentação final | ⬜ |

Regra de trabalho: um módulo por vez, sempre com objetivo → arquivos
alterados → implementação → teste → resultado mostrado → correção →
próximo. Não acumular módulos sem testar.

---

## 2026-09-11 — ETAPA 4: modelo de dados completo

### O que foi feito

25 models SQLAlchemy (arquivos em `backend/app/models/`), cobrindo
todas as entidades do documento de referência mais as auxiliares
explicitamente permitidas (item 32: "considere também entidades
auxiliares necessárias"): `NotificationPreference` e `LifeEvent`.

Decisões de modelagem que valem registrar:

- **UUID como chave primária em toda tabela** (não serial
  incremental) — não vaza contagem de usuários/registros por quem
  inspeciona um ID.
- **`FunctionalIndicator` como fato normalizado**: todo dado bruto
  (check-in, evento de tarefa, rotina, observação, adesão a
  medicação) é traduzido para uma linha `(usuário, indicador, dia,
  fonte, valor)`. É a única tabela que o motor de baseline/desvio lê
  — não precisa saber de onde o dado veio. Isso é o que implementa o
  item 38 do documento ("construa interfaces que permitam trocar o
  motor analítico sem reescrever o resto do produto").
- **Permissão como tabela `(relacionamento, permission_key)`**, uma
  linha por permissão, em vez de colunas booleanas fixas — permite
  testar cada permissão isoladamente (exigido nos itens 45/70) e
  adicionar permissão nova sem migration estrutural.
- **Nada é sobrescrito quando representa histórico comportamental**:
  `TaskEvent`, `RoutineEvent`, `Alert` e `DeviationEvent` são
  event-sourced (item 33) — o estado "atual" é sempre a última linha,
  nunca uma coluna mutável.
- **Baseline é versionado** (`Baseline.version` + `period_start`/
  `period_end`), preparado pro cenário do item 56 (mudança de
  emprego não pode ser lida como deterioração pra sempre).
- **Soft delete só onde importa reversibilidade/retenção legal**
  (`User.deactivated_at`, `Medication.discontinued_at`); o resto usa
  `ON DELETE CASCADE` de verdade porque não há motivo pra manter, por
  exemplo, uma tarefa órfã depois que o usuário some.

### Bug real encontrado e corrigido

O autogenerate do Alembic cria os tipos `ENUM` nativos do Postgres no
`upgrade()`, mas **não** gera o `DROP TYPE` correspondente no
`downgrade()` — limitação conhecida da combinação
Alembic+SQLAlchemy+Postgres enums. Sem correção, um ciclo
`downgrade` → `upgrade` falha com `type "x" already exists`. Testado,
reproduzido e corrigido nesta sessão: a migration
`47f79baac7ca_modelo_de_dados_completo.py` agora derruba os 27 tipos
enum explicitamente no fim do `downgrade()`. Ciclo completo
`upgrade → downgrade → upgrade` validado depois da correção.

### Verificação (não assumida — executada)

- `alembic revision --autogenerate` gerou as 25 tabelas sem erro.
- `alembic upgrade head` aplicado contra Postgres real.
- Ciclo `upgrade → downgrade → upgrade` executado e limpo (0 tabelas
  e 0 enums orfãos depois do downgrade; upgrade seguinte sem erro).
- 7 testes automatizados novos (`tests/test_models.py`), cobrindo:
  check-in único por usuário/dia, todos os indicadores de check-in
  opcionais (item 6), permissão granular por relacionamento (item
  45/70), rejeição de permissão duplicada, cascade de exclusão de
  usuário → perfil.
- `pytest -q` → **7 passed**, sem warnings.

---

## 2026-09-12 — ETAPA 6: autenticação

### O que foi feito

- Cadastro (`POST /api/v1/auth/register`), login
  (`POST /api/v1/auth/login`), refresh com rotação
  (`POST /api/v1/auth/refresh`), logout
  (`POST /api/v1/auth/logout`), "quem sou eu"
  (`GET /api/v1/auth/me`), troca de senha
  (`POST /api/v1/auth/change-password`) e recuperação de senha em
  duas etapas (`/password-reset/request` + `/password-reset/confirm`).
- **Duas famílias de token, de propósito**: access token é um JWT
  curto (15 min), stateless, nunca revogável antes de expirar sozinho.
  Refresh token e token de reset são valores opacos de alta entropia,
  guardados **hasheados** (SHA-256) em tabela própria
  (`RefreshSession`, `PasswordResetToken`) — é isso que permite
  revogação de verdade (logout, troca de senha, reset).
- **Rotação de refresh token**: todo uso de um refresh token o
  invalida e emite um novo. Testado explicitamente: reutilizar um
  refresh token já trocado falha com 401.
- **Proteção contra abuso sem infraestrutura nova** (item 35): 5
  tentativas de login erradas bloqueiam a conta por 15 minutos
  (`User.failed_login_attempts`/`locked_until`). Um rate limit por IP
  na borda é a camada que falta quando o volume justificar.
- **Nunca revela se um e-mail existe**: login com e-mail inexistente
  e login com senha errada respondem o mesmo 401; pedido de reset de
  senha sempre responde 202, exista ou não a conta.
- **Decisão explícita registrada**: v1 não faz verificação de e-mail
  no cadastro (conta ativa na hora) porque nenhum provedor de envio
  de e-mail está conectado ainda — mesma razão pela qual o token de
  recuperação de senha ainda não é entregue por e-mail de verdade. Os
  dois ficam resolvidos juntos quando a ETAPA 22 (notificações) ligar
  o canal de e-mail. Até lá, o fluxo de reset já existe e está
  testado ponta a ponta — só falta o transporte.

### Verificação

- Nova migration (`65fb648a26f3`) aplicada contra Postgres real,
  testada em ciclo upgrade→downgrade→upgrade.
- 15 testes novos em `tests/test_auth.py` (cadastro, duplicidade de
  e-mail, senha fraca, login válido/inválido, bloqueio por tentativas,
  `/me` com e sem token, rotação e revogação de refresh token, logout,
  troca de senha com revogação de outras sessões, fluxo completo de
  reset de senha, não-reuso de token de reset).
- `pytest -q` → **22 passed** (7 da ETAPA 4 + 15 novos).
- Smoke test manual com `curl` contra o servidor rodando de verdade
  (fora da suíte de testes): registro → login → `/me` → refresh →
  reuso do refresh antigo rejeitado (401) → `/me` sem token rejeitado
  (401). Mesmo resultado dos testes automatizados.

---

## 2026-09-12 — ETAPA 7 + 14 + 16: autorização, pessoas de confiança e observações externas

### Por que três etapas de uma vez

Autorização sem um recurso concreto pra proteger é abstração
impossível de testar direito — "escrever a checagem" sem nada que ela
proteja não prova nada. Pessoas de confiança (item 14) é o próprio
cenário de autorização mais importante do produto, e observação
externa (item 16) é exatamente o exemplo que os itens 45/70/71 do
documento de referência usam pra especificar o comportamento exigido.
Construir os três junto é tratá-los como um módulo coeso, em vez de
criar uma etapa intermediária ("autorização") que não faz nada
sozinha.

### O que foi feito

- `app/services/authorization_service.py`: `require_relationship_permission`
  — o único lugar do backend que decide se uma pessoa de confiança
  pode agir sobre a conta de outra pessoa. Nunca cacheado: relê
  relacionamento e permissão do banco a cada chamada (item 71 —
  revogação vale imediatamente, não na próxima renovação de token).
  Toda negação é registrada em `AuditLog` (item 31/54) sem nunca
  gravar o dado em si, só qual permissão foi negada.
- `app/api/deps.py`: `require_relationship_permission(permission_key)`
  — dependency factory do FastAPI que embrulha o service acima. 404
  se o relacionamento não existe **para este usuário** (nunca revela
  se existe para outro — mesmo princípio anti-enumeração da
  autenticação); 403 se existe mas a permissão não está concedida.
- `POST /api/v1/trusted-people/invite`, `/accept`, `GET /trusted-people`,
  `PUT /{id}/permissions`, `POST /{id}/revoke`,
  `POST /{id}/observations` (só quem tem `RECORD_OBSERVATION`
  concedida), `GET /{id}/observations` (só o dono da conta observada).
- **Convite endereçado a um e-mail específico**: aceitar com o token
  certo mas logado com outra conta é rejeitado — o token sozinho não
  basta (item 45).
- **Revogar o relacionamento desliga toda permissão concedida**, uma
  linha de `AuditLog` por permissão desligada — dá pra ver no log que
  uma relação inteira foi revogada, não só uma permissão isolada.
- **Simplificação de escopo, registrada aqui**: convite não expira em
  v1 (só é revogável manualmente enquanto pendente). Adicionar
  expiração automática é uma migration pequena quando isso importar
  de verdade — não vale a complexidade agora.

### Verificação

- Zero migrations novas: as tabelas já existiam desde a ETAPA 4.
- 11 testes novos em `tests/test_trusted_people.py`, cobrindo
  literalmente os cenários obrigatórios do documento: pessoa de
  confiança com relação ativa mas sem a permissão específica → 403 e
  fica auditado; permissão concedida não vaza pra nenhuma outra ação;
  revogação bloqueia a próxima tentativa na hora; **alguém sem
  nenhuma relação recebe 404, não 403** (403 confirmaria que o
  relacionamento existe); só o dono pode conceder permissão ou
  revogar — a própria pessoa de confiança não pode.
- Um bug real do próprio teste (não do produto) apareceu e foi
  corrigido na hora: comparação contra um dict tratado como objeto.
  Fica registrado porque é exatamente o tipo de erro que "rodar o
  teste" pega e "ler o código" não pega.
- `pytest -q` → **33 passed**.
- Smoke test manual via `curl` contra o servidor real, replicando o
  fluxo completo (convite → token lido do banco, como um serviço de
  e-mail externo faria → aceite → tentativa negada → permissão
  concedida → observação aceita → revogação → tentativa seguinte
  negada). Mesmo resultado dos testes automatizados.

### Nota tardia: bug de isolamento de teste encontrado depois

Rodando a suíte de novo numa sessão seguinte (banco de dev com dados
reais deixados por testes manuais de `curl` anteriores), 4 consultas
em `tests/test_trusted_people.py` que assumiam a tabela
`trusted_person_relationships`/`audit_logs` vazia (`.query(...).one()`
sem filtro) quebraram com `MultipleResultsFound` — não é bug de
produto, é teste que só funcionava por acaso enquanto o banco estava
limpo. Corrigido filtrando cada consulta pelo dado do próprio teste
(e-mail do convite, ou `relationship_id` no `log_metadata` do
`AuditLog`). Lição registrada: teste de integração contra um banco
real (não só transação isolada) precisa sempre filtrar pelo que ele
mesmo criou, nunca assumir tabela vazia — mesmo com o isolamento por
SAVEPOINT funcionando perfeitamente para o resto (rollback automático
a cada teste), dado de fora da transação do teste (deixado por uma
sessão anterior) continua visível em READ COMMITTED.

---

## 2026-09-12 — ETAPA 8 + 9: usuários, perfil e onboarding guiado

### Por que as duas juntas

O onboarding (item 4) não é um questionário descartável — é o
preenchimento progressivo do próprio `Profile`, que já existia desde
a ETAPA 4 e é reaproveitado depois (tom de interface, contexto para
o motor de baseline, sinais autorreconhecidos de piora). Criar uma
tabela de "respostas de onboarding" separada duplicaria dado sem
necessidade; criar uma ETAPA "onboarding" que não mexe em nenhum
model novo não seria um módulo coeso sozinho.

### O que foi feito

- `POST /api/v1/profile` (cria — 1:1 com o usuário, só
  `display_name` é obrigatório; todo o resto é texto livre que pode
  legitimamente ficar vazio), `GET /api/v1/profile` (404 se ainda não
  criado — é assim que o frontend sabe se deve mandar a pessoa pro
  onboarding), `PATCH /api/v1/profile` (parcial — só os campos
  enviados mudam, via `model_dump(exclude_unset=True)` no schema;
  campo omitido nunca apaga o que já estava salvo), `POST
  /api/v1/profile/complete-onboarding` (idempotente — confirmar de
  novo não é erro; não exige todo campo preenchido porque validar
  campo a campo criaria fricção sem benefício real: "dificuldades
  recorrentes" vazio é uma resposta válida).
- Perfil é estritamente privado ao próprio dono — não existe rota que
  aceite `user_id` de outra pessoa; a única forma de ver/editar é
  através do usuário autenticado do token.

### Verificação

- 7 testes novos (`tests/test_profile.py`): 404 antes de criar,
  criação, criação duplicada rejeitada (409), PATCH parcial não
  apaga campo não enviado, PATCH antes de criar (404), conclusão de
  onboarding idempotente (segunda chamada devolve o mesmo timestamp
  da primeira), perfil de um usuário nunca aparece pra outro.
- `pytest -q` → **40 passed** (33 anteriores + 7 novos).
- Smoke test manual via `curl` contra o servidor real: registro/login
  → 404 em `/profile` antes de criar → criar → PATCH parcial (campo
  não enviado permaneceu) → concluir onboarding. Mesmo resultado dos
  testes automatizados.

### Nota de infraestrutura: ponte com o computador do usuário

Nesta sessão uma pasta local (`gancho` na Área de Trabalho) foi
conectada, permitindo sincronizar o projeto atual direto no
computador do usuário em vez de só entregar `.zip` a cada etapa
(`gancho_sync_current` dentro dessa pasta é a cópia atual e
completa). Uma tentativa de limpar cópias antigas/parciais que já
estavam na pasta (de zips extraídos em sessões anteriores) foi
bloqueada pelo classificador de modo automático (operação
irreversível/destrutiva no computador do usuário) — o pedido de
permissão de exclusão não chegou a ser oferecido ao usuário para
confirmação, foi negado automaticamente. Ficou registrado para o
usuário apagar manualmente o que sobrou; a sincronização em si (via
`device_commit_files`, que sobrescreve arquivo por arquivo com guarda
de mtime) funciona normalmente e será o canal usado daqui pra frente
além do `.zip`.

---

## 2026-09-12 — ETAPA 10: tarefas e eventos de tarefa

### O que foi feito

- `Task.status` nunca é escrito direto por nenhuma rota — toda
  transição passa por uma função de ação em `task_service.py`
  (`start`, `resume`, `pause`, `postpone`, `complete`, `cancel`) que
  grava o `TaskEvent` imutável primeiro e só então atualiza o status e
  os contadores desnormalizados (item 33). Uma tabela `_ALLOWED_FROM`
  central define de que estados cada ação pode partir — terminal
  (`completed`/`cancelled`) nunca é origem de transição; uma tarefa
  terminada não reabre (se a pessoa quer retomar, cria uma nova —
  mantém o histórico honesto sobre o que de fato aconteceu).
- **Adiar exige motivo (`TaskFailureReasonType`), cancelar não**
  (item 8) — adiar é o evento que o motor de função executiva lê pra
  descobrir o gargalo ("esqueci" vs "não consegui começar" vs "fiquei
  ansioso" mudam a hipótese causal); cancelar pode ser só "a tarefa
  deixou de fazer sentido", sem necessariamente ser evitação.
- `POST /api/v1/trusted-people/{id}/tasks/suggest`: pessoa de
  confiança com a permissão `SUGGEST_TASK` (nível 2 — "Apoiar" — do
  esquema de permissões do documento) cria uma tarefa **na conta do
  dono**, marcada com `origin=trusted_person_suggestion` e o
  `relationship_id` de onde veio. Reaproveita literalmente o mesmo
  `require_relationship_permission` da ETAPA 7 — mesmo teste de
  "permissão errada não dá acesso" replicado aqui.
- **Decisão de escopo registrada**: `CREATE_TASK` e `HELP_WITH_TASK`
  (as outras duas permissões relacionadas a tarefa já modeladas desde
  a ETAPA 4) ficam sem uso por enquanto — o documento não especifica
  uma diferença de comportamento clara entre "sugerir" e "criar" tarefa
  além do nível de permissão nomeado, e "ajudar com" (body doubling)
  depende de uma sessão compartilhada em tempo real que é a sua
  própria etapa (não faz sentido antecipar sem um caso de uso
  concreto). Retomado quando o documento/uso real pedir.

### Verificação

- 11 testes novos (`tests/test_tasks.py`): criação loga evento
  `created`; iniciar seta `started_at` e incrementa `attempt_count`;
  iniciar tarefa já concluída → 409; adiar sem motivo → 422 (schema
  exige o campo); adiar incrementa `postponed_count`; tarefa adiada
  pode ser iniciada de novo; ciclo completo
  iniciar→pausar→retomar→concluir com histórico de eventos na ordem
  certa; cancelar sem motivo é permitido; PATCH nunca muda `status`;
  tarefa é privada ao dono; sugestão de pessoa de confiança com a
  permissão certa funciona, com a permissão errada dá 403.
- `pytest -q` → **51 passed** (40 anteriores + 11 novos).
- Smoke test manual via `curl` contra o servidor real: criar → iniciar
  → adiar sem motivo rejeitado (422) → adiar com motivo → concluir →
  tentar iniciar de novo rejeitado (409) → histórico de eventos na
  ordem certa (`created, started, postponed, completed`). Mesmo
  resultado dos testes automatizados.

---

## 2026-09-12 — ETAPA 11: check-ins

### O que foi feito

- `POST /api/v1/checkins` (cria o check-in de uma data — por padrão
  "hoje" resolvido no fuso horário do `Profile`, caindo pra UTC se o
  perfil ainda não existe), `GET /api/v1/checkins/{data}`,
  `PATCH /api/v1/checkins/{data}` (revisão parcial do mesmo dia),
  `GET /api/v1/checkins` (histórico, filtrável por intervalo de
  datas, paginado por `limit`).
- **Item 6 aplicado ao pé da letra**: todo indicador (humor, energia,
  ansiedade, capacidade de começar tarefas, disposição pra interagir,
  qualidade do sono, sensação geral de funcionamento) é opcional na
  coluna — a única regra é "pelo menos um campo preenchido" (ou
  `extra_answers` não vazio), validada no schema Pydantic, não como
  constraint de banco (um check-in não precisa ser completo pra valer
  a pena registrar).
- Um check-in por usuário/dia (`UniqueConstraint` do model, ETAPA 4);
  tentar criar de novo no mesmo dia dá 409 — a forma de revisar é o
  PATCH, nunca um segundo POST.

### Verificação

- 8 testes novos (`tests/test_checkins.py`): check-in vazio rejeitado
  (422); criação usa a data de hoje por padrão; segundo check-in no
  mesmo dia rejeitado (409); PATCH revisa sem apagar campo não
  enviado; PATCH em data sem check-in é 404; get por data e
  listagem/histórico em ordem decrescente; check-in é privado ao
  dono; `extra_answers` sozinho já satisfaz o mínimo.
- `pytest -q` → **59 passed** (51 anteriores + 8 novos).
- Smoke test manual via `curl` contra o servidor real: vazio rejeitado
  → criar → duplicado no mesmo dia rejeitado → PATCH parcial →
  histórico. Mesmo resultado dos testes automatizados.

---

## 2026-09-12 — ETAPA 12: rotinas e eventos de vida

### O que foi feito

- `POST /api/v1/routines` (declara a rotina de referência — só uma
  ativa por vez), `GET /routines/current`, `GET /routines/current/events`
  (histórico de mudanças da versão atual), `GET /routines` (todas as
  versões, mais antiga tem `period_end` preenchido), `POST
  /routines/new-version` (fecha a atual e abre outra do zero).
- **Duas formas de mudar a rotina, de propósito diferente** (o
  próprio comentário do model já apontava isso, faltava a regra de
  negócio): `PATCH /routines/current` é edição corriqueira — cada
  campo alterado vira um `RoutineEvent` imutável (item 33), mas a
  versão não muda; `POST /routines/new-version` é virada de vida
  (item 56/57) — fecha a rotina atual (`period_end`) e declara uma
  nova do zero, pra um desvio contra o baseline anterior não ser lido
  como deterioração depois de uma mudança real de contexto (novo
  emprego, mudança de cidade). PATCH que reenvia o mesmo valor não
  gera evento (nada mudou de fato).
- `POST/GET /api/v1/life-events` — registro simples de eventos de
  vida (item 57: viagem, novo emprego, doença, mudança...), contexto
  que o motor de baseline vai usar mais à frente; por ora é só
  CRUD (create + list) desacoplado da rotina — a conexão analítica
  entre os dois é trabalho da ETAPA 17/18, não desta.

### Verificação

- 9 testes novos (`tests/test_routines.py`): 404 antes de criar;
  criação; segunda criação enquanto uma está ativa é rejeitada (409);
  PATCH loga um `RoutineEvent` por campo mudado com `old_value`/
  `new_value` corretos; PATCH com o mesmo valor não loga nada;
  nova versão fecha a anterior sem apagar histórico; rotina é privada
  ao dono; evento de vida cria/lista; evento de vida é privado ao
  dono.
- `pytest -q` → **68 passed** (59 anteriores + 9 novos).
- Smoke test manual via `curl` contra o servidor real: 404 → criar →
  PATCH (evento logado) → nova versão (fecha a v1, abre a v2) →
  histórico mostrando as duas → evento de vida. Mesmo resultado dos
  testes automatizados.

---

## 2026-09-12 — ETAPA 13: medicamentos e adesão

### O que foi feito

- CRUD de `Medication` (`POST/GET/PATCH /medications`,
  `POST /{id}/discontinue` — soft delete idempotente; histórico de
  adesão continua valendo pro motor de estabilidade mesmo depois de
  suspenso, item 12), horários aninhados (`MedicationSchedule`, hora
  do dia + dias da semana opcionais — omitido = todo dia) e registro
  de adesão (`MedicationEvent`) aninhado ao horário.
- **Regra central do item 13, reforçada em código, não só em
  comentário**: `status='taken'` nunca leva motivo; qualquer outro
  status (`not_taken`, `skipped_deliberately`, `unavailable`) exige
  `skip_reason` — um `model_validator` no schema recusa os dois casos
  errados antes de chegar no service. Nada aqui gera recomendação de
  dose, horário ou "tome agora" — só registra o que a pessoa informa
  sobre o próprio tratamento.
- **`FORGOT_TO_CONFIRM` reservado pro futuro job automático** (ETAPA
  22 — quando a janela de confirmação de uma dose expira sem
  resposta, o próprio sistema registraria isso): não é um status que
  a rota aceita da pessoa via `POST`, só os quatro que fazem sentido
  como ação humana.
- **Decisão de escopo**: `MedicationSchedule` não tem `DELETE` — como
  os eventos de adesão são ligados ao horário por `ON DELETE CASCADE`,
  apagar um horário apagaria histórico comportamental de verdade
  (mesmo raciocínio de nunca sobrescrever o que já aconteceu). Ajustar
  hora/dias é `PATCH`; não existe hoje um caso de uso real pra
  "remover" um horário que justifique perder adesão registrada nele.

### Verificação

- 10 testes novos (`tests/test_medications.py`): criação/listagem;
  descontinuar é idempotente e some da listagem padrão (mas aparece
  com `include_discontinued=true`); PATCH atualiza só o enviado;
  criação de horário e rejeição de dia da semana inválido (422);
  `taken` sem motivo passa, os outros três sem motivo são rejeitados
  (422); `forgot_to_confirm` não pode ser escolhido pela pessoa (422);
  eventos de horários diferentes do mesmo medicamento aparecem juntos
  na listagem agregada; medicamento/horário/evento são privados ao
  dono (404 em cada nível pra quem não é dono, nunca 403 que
  revelaria a existência).
- `pytest -q` → **78 passed** (68 anteriores + 10 novos).
- Smoke test manual via `curl` contra o servidor real: criar
  medicamento → criar horário → registrar `taken` → registrar
  `not_taken` sem motivo rejeitado (422) → registrar `not_taken` com
  motivo → descontinuar → listagem padrão vem vazia. Mesmo resultado
  dos testes automatizados.

---

## 2026-09-12 — ETAPA 17: baseline (motor analítico)

### O que foi feito

Duas peças, deliberadamente separadas:

- **Ingestão** (`app/services/indicator_service.py`): a única ponte
  entre dado bruto e `FunctionalIndicator`. `checkin_service`,
  `task_service` e `medication_service` chamam essas funções na mesma
  transação em que já gravam o próprio dado (nenhum job separado
  ainda — decisão consciente, ver abaixo). `sync_checkin_indicators`
  grava `mood`/`energy`/`anxiety`/`ability_to_start_tasks`;
  `sync_task_event_indicators` **recalcula do zero** (nunca
  incrementa) as contagens de `started`/`postponed`/`completed` do
  dia a partir do próprio `TaskEvent`; `sync_medication_adherence_indicator`
  grava a fração tomada/agendada do dia (sem dose agendada, não
  escreve nada — "sem dado" ≠ "aderência zero").
- **Motor de baseline** (`app/services/baseline_service.py`): lê só
  de `FunctionalIndicator`, nunca das tabelas de origem — é o que o
  item 38 pede ("trocar o motor sem reescrever o resto"). Estatística
  deliberadamente simples (`statistics` da stdlib, sem numpy/pandas):
  média, mediana, desvio padrão, frequência de registro (amostra /
  janela), tendência linear (regressão simples por índice de dia,
  não por posição na lista — dia sem registro é buraco na tendência,
  não é "pulado"), valor mais recente e o quanto ele se afasta da
  média.
- **Duas operações de mudança, mesmo padrão já usado em rotinas**:
  `POST /baseline/{indicator}/recompute` sobe um `BaselineMetric`
  novo dentro da MESMA versão (o que um job noturno faria, quando
  existir — ETAPA 22); `POST /baseline/{indicator}/recalibrate`
  fecha a versão ativa e abre outra do zero, reservado pra depois de
  uma virada de vida (item 56/57) — o baseline antigo não classifica
  a rotina nova como anormal pra sempre.
- `GET /indicators` — leitura direta do fato normalizado, pra
  transparência (a pessoa pode ver exatamente o que alimenta o
  próprio baseline, sem esperar a ETAPA 20 de explicabilidade).

### Decisões de escopo registradas

- Só `mood`/`energy`/`anxiety`/`ability_to_start_tasks` do check-in
  têm `IndicatorKey` mapeado. `sleep_quality` (escala 1-5) não é o
  mesmo dado que `SLEEP_HOURS`; `willingness_to_interact` não virou
  `SOCIAL_CONTACT` de propósito — misturar "vontade de interagir"
  (subjetivo) com "contato social" (comportamental/contável) violaria
  o próprio item 38. `SLEEP_HOURS`, `WAKE_TIME_MINUTES`,
  `LEFT_HOME`, `SOCIAL_CONTACT`, `ACTIVITY_LEVEL`, `AVOIDANCE_LOAD`
  ficam sem fonte de dado real (dependem de rotina diária ou sensor
  passivo — nenhum existe no MVP); o design de fato normalizado
  significa que ligar uma fonte nova no futuro é só escrever um
  `sync_*`, nunca mexer no motor.
- Ingestão acontece **na mesma transação** de quem gera o dado, não
  num job assíncrono — mais simples de implementar e testar agora, e
  correto (item 65: não complicar sem necessidade); revisitar se o
  volume um dia justificar desacoplar.
- `recompute_baseline` nunca bloqueia por amostra pequena (calcula
  mesmo com `sample_size=1`) — o `sample_size` fica visível na
  resposta pra quem for decidir se o número já é confiável; **exigir
  uma amostra mínima antes de gerar alerta é trabalho da ETAPA 18**
  (motor de desvio), não deste módulo.

### Verificação

- 11 testes novos (`tests/test_baseline.py`): check-in alimenta
  indicador certo; PATCH atualiza o indicador (upsert, não duplica);
  eventos de tarefa alimentam as contagens certas; adesão a
  medicação calcula a fração certa; recompute sem dado nenhum é
  rejeitado (409); recompute cria versão 1 com a métrica certa
  (conferido a mão: média, desvio padrão, tendência e diferença pro
  baseline); recompute de novo sobe métrica sem trocar versão;
  histórico mostra todas as métricas já calculadas; listagem agregada
  de baselines ativos; recalibrar fecha a versão antiga e abre outra;
  tudo privado ao dono.
- `pytest -q` → **89 passed** (78 anteriores + 11 novos).
- Smoke test manual via `curl` contra o servidor real: dois check-ins
  em dias diferentes → indicadores brutos corretos → recompute
  (média 3.0, desvio √2≈1.414, tendência 2.0, diferença +1.0 — bate
  a mão) → recalibrar (v2 sem métrica, v1 fechada com `period_end`).
  Mesmo resultado dos testes automatizados.

Próximo passo: **ETAPA 18 — Motor de desvio** (os 4 motores separados
do item 9-12 — Executivo, Evitação, Ativação, Estabilidade — que
comparam o valor recente de cada indicador contra o baseline desta
etapa e decidem se o desvio é persistente o suficiente pra importar;
é aqui que a amostra mínima confiável finalmente vira regra).

## 2026-09-15 — Correções pós-implantação: e-mail real e convite de rede de confiança

Duas lacunas reais, achadas só depois do deploy em produção (ETAPA 35),
ao testar o sistema de e-mail de ponta a ponta pela primeira vez com
credenciais reais — nenhuma delas era visível pelos 226 testes
automatizados existentes até então, porque nenhum teste exercitava a
entrega de e-mail de verdade nem a tela que o link de e-mail abre.

### 1. Provedor de e-mail: SMTP não funciona no plano usado

Configurar SMTP (Gmail) travava a requisição de reset de senha por
tempo indefinido, em vez de falhar rápido. Causa raiz: o provedor de
hospedagem usado bloqueia SMTP de saída por completo nos planos
gratuitos/trial, pra evitar abuso — a porta fica "sem resposta" (não
"conexão recusada"), e o código não tinha timeout de rede, então a
requisição nunca liberava o worker que a atendia.

- `app/core/email.py`: `RESEND_API_KEY` (provedor de e-mail via API
  HTTPS, porta 443 — nunca bloqueada por essa política) passou a ter
  prioridade sobre SMTP; timeout explícito de 10s nos dois caminhos;
  falha de envio nunca propaga pra quem chamou `send_email` — só
  registra no log, nunca derruba cadastro/reset.
- Achado um segundo problema no mesmo teste: o remetente usado pro
  Resend não pode ser um e-mail qualquer (ex.: Gmail do usuário) — o
  provedor rejeita com 403 por ser falsificação de remetente. Sem um
  domínio próprio verificado, o remetente cai no domínio de teste do
  provedor, que só entrega pro e-mail da própria conta cadastrada
  nele. **Limitação que continua valendo**: enquanto nenhum domínio
  for verificado em resend.com/domains, e-mail de sistema (reset,
  convite, notificação) só chega de verdade pra quem tem conta no
  provedor de e-mail — pra qualquer outro destinatário, cai só no
  registro interno (mesmo comportamento seguro de antes, nunca quebra
  o fluxo).
- `RESEND_FROM_EMAIL` (opcional): quando um domínio for verificado,
  aponta o remetente pra ele, sem mudar código nenhum.

### 2. Bug real: convite de pessoa de confiança nunca chegava a ninguém

Achado ao seguir o mesmo teste de ponta a ponta pro fluxo de convite.
Desde a ETAPA 14 (rede de confiança), `invite_trusted_person` sempre
gerou e gravou o código do convite no banco — e sempre gravou um
`AuditLog` com ação `INVITE_SENT`, apesar de nenhum e-mail jamais ter
sido enviado de fato. A resposta da API (`RelationshipPublic`) também
nunca incluiu o código, então não existia nem forma automática nem
forma manual da pessoa convidada saber que tinha sido convidada — o
convite ficava permanentemente preso no servidor.

- `trust_service.invite_trusted_person` agora chama `email.send_email`
  de verdade (mesmo caminho do reset de senha — nunca lança, só loga
  se falhar).
- Novo schema `InviteCreatedResponse` (só na resposta de
  `POST /trusted-people/invite`, nunca em `GET /trusted-people` nem em
  qualquer outra resposta de relacionamento) inclui `invite_token` —
  quem convidou sempre tem o código/link pra copiar e mandar por
  qualquer canal, mesmo se o e-mail não chegar.
- Frontend: `TrustedPeoplePage` mostra o link de aceite depois de cada
  convite bem-sucedido (reforço manual, sempre visível, não só quando
  o e-mail falha — o backend não confirma entrega, então não dá pra
  saber do lado do cliente se é necessário); `AcceptInvitePage` lê
  `?token=` da URL e pré-preenche, pra o link do e-mail abrir direto
  no formulário em vez de exigir colar o código na mão.
- Teste de regressão novo (`test_invite_response_includes_token_but_list_does_not`):
  confirma que o token na resposta do convite é o token real (usável
  pra aceitar) e que `GET /trusted-people` continua sem expô-lo.

### Por que só apareceu agora

As duas lacunas já existiam desde a implementação original (ETAPA 22
pro e-mail, ETAPA 14 pro convite) — nenhuma foi introduzida por
mudança recente. Os testes automatizados sempre validaram a metade
"escreve no banco" de cada fluxo, nunca a metade "chega pra fora"
(entrega de e-mail real, ou a página que o link do e-mail abre).
Reforça a lição já registrada na ETAPA 27: testes automatizados
provam que o código faz o que o teste pede, não que o produto
funciona ponta a ponta pra quem usa de fora.

### Verificação

- 226 testes de backend passam (225 anteriores + 1 novo).
- 25 testes de frontend + build (`tsc` + `vite`) continuam limpos.
- Verificado em produção: reset de senha entrega e-mail de verdade
  pro Resend (confirmado sem erro no log); convite grava o token
  corretamente e a resposta da API o inclui — sem regressão no
  isolamento de quem cada relacionamento pertence.
