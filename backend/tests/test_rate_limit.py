"""
ETAPA 35 — rate limit por IP (`app/core/rate_limit.py`).

Dois testes distintos de propósito, não um só:

1. Que o limiter DE PRODUÇÃO usado pelo app real fica desligado fora
   de produção — isso é o que garante que a suíte inteira (que bate
   dezenas de vezes por minuto nas mesmas rotas de auth) não vira
   flaky. `Limiter.enabled` é fixado na construção a partir de
   `settings.environment` lido uma vez no import do módulo — não dá
   pra simplesmente trocar `environment` num teste e esperar que o
   objeto já construído mude de comportamento (diferente do
   middleware de cabeçalhos de segurança, que lê `settings` a cada
   requisição). Testar isso direto no objeto é mais simples e mais
   honesto do que fingir produção contra o app inteiro.
2. Que a MECÂNICA de limitação (decorator + middleware + exception
   handler, o mesmo padrão de app/main.py) de fato devolve 429 depois
   do limite — provado contra uma app mínima e isolada, com o limiter
   forçado a `enabled=True`, pra não depender de nenhuma variável de
   ambiente nem arriscar vazar estado entre testes do resto da suíte.
"""
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.rate_limit import limiter as production_limiter


def test_production_limiter_is_disabled_outside_production():
    """`ENVIRONMENT=development` (padrão de dev/test) → `enabled=False`, senão a suíte inteira seria flaky."""
    assert production_limiter.enabled is False


def test_rate_limit_mechanism_returns_429_after_the_configured_limit():
    test_limiter = Limiter(key_func=get_remote_address, enabled=True)

    app = FastAPI()
    app.state.limiter = test_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/limited")
    @test_limiter.limit("3/minute")
    def limited_route(request: Request):
        return {"ok": True}

    client = TestClient(app)
    for _ in range(3):
        assert client.get("/limited").status_code == 200

    fourth = client.get("/limited")
    assert fourth.status_code == 429
