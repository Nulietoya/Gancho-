"""
Ponto de entrada da API.

Nesta etapa (ETAPA 3 do plano) o objetivo é só provar que a
aplicação sobe, conecta no banco e responde. Routers de domínio
(auth, checkins, tasks, ...) são plugados aqui conforme cada ETAPA
seguinte é implementada.

Desde a ETAPA 22, o `lifespan` também liga o `BackgroundScheduler`
(ciclo noturno de baseline/desvio/alerta/adesão + entrega periódica
de notificações represadas) — nunca dispara durante os testes: o
`TestClient` usado em `tests/conftest.py` é instanciado sem `with`,
então o protocolo ASGI de lifespan nunca é acionado ali (documentado
também em `docs/decisions.md`).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.api.v1.account import router as account_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.baseline import indicators_router, router as baseline_router
from app.api.v1.checkins import router as checkins_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.deviation import router as deviation_router
from app.api.v1.intervention import router as intervention_router
from app.api.v1.medications import router as medications_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.personal_plan import router as personal_plan_router
from app.api.v1.profile import router as profile_router
from app.api.v1.routines import life_events_router, router as routines_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.trusted_people import router as trusted_people_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.rate_limit import limiter
from app.core.scheduler import shutdown_scheduler, start_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API do Gancho — sistema de apoio a padrões de funcionamento pessoal.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ETAPA 35: rate limit por IP (só ativo em produção — ver
# app/core/rate_limit.py). O limite por rota é aplicado com
# `@limiter.limit(...)` diretamente nas rotas sensíveis de
# app/api/v1/auth.py, não aqui.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ETAPA 30-32 (revisão de segurança): cabeçalhos de resposta que não
# custam nada e fecham brechas comuns de navegador — nenhum framework
# de auth ou de rede aqui, só resposta HTTP mesmo. `/docs`/`/redoc`
# (Swagger UI/ReDoc) carregam JS de um CDN (jsdelivr) pra renderizar a
# página, então recebem uma CSP mais permissiva; toda outra rota é API
# JSON pura e não deveria executar nenhum script vindo de lugar nenhum,
# então recebe `default-src 'none'`.
_DOCS_PATHS = {"/docs", "/redoc"}


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path in _DOCS_PATHS:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; img-src 'self' fastapi.tiangolo.com data:; "
            "worker-src 'self' blob:"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'"
    if settings.environment == "production":
        # HSTS só faz sentido (e só é seguro) quando o tráfego já é
        # HTTPS de verdade — em dev/test o header seria ignorado pelo
        # navegador em http:// mesmo, mas evitar mandá-lo fora de
        # produção evita confusão ao inspecionar respostas locais.
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


app.include_router(account_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(baseline_router, prefix="/api/v1")
app.include_router(indicators_router, prefix="/api/v1")
app.include_router(checkins_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(deviation_router, prefix="/api/v1")
app.include_router(intervention_router, prefix="/api/v1")
app.include_router(medications_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(personal_plan_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(routines_router, prefix="/api/v1")
app.include_router(life_events_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(trusted_people_router, prefix="/api/v1")


@app.get("/health", tags=["infra"])
def health() -> dict:
    """Liveness/readiness check: confirma que o processo e o banco respondem."""
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "environment": settings.environment,
        "database": "ok" if db_ok else "unreachable",
    }
