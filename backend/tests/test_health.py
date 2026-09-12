def test_health_reports_ok_and_database_connected(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_responses_carry_baseline_security_headers(client):
    """ETAPA 30-32: X-Content-Type-Options/X-Frame-Options/Referrer-Policy em toda resposta."""
    response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_json_api_routes_get_a_locked_down_csp_but_docs_get_a_permissive_one(client):
    api_response = client.get("/health")
    assert api_response.headers["content-security-policy"] == "default-src 'none'"

    docs_response = client.get("/docs")
    docs_csp = docs_response.headers["content-security-policy"]
    assert "cdn.jsdelivr.net" in docs_csp
    assert docs_csp != "default-src 'none'"


def test_hsts_header_only_sent_when_environment_is_production(client, monkeypatch):
    """
    ETAPA 33-34: o branch `environment == "production"` do middleware
    de segurança (ETAPA 30-32) nunca era exercitado por nenhum teste
    — testes sempre rodam com `environment=development` (achado via
    `pytest --cov`). `app.main.settings` é o mesmo objeto que o
    middleware lê a cada requisição, então trocar `.environment` nele
    é suficiente pra simular produção sem reconstruir a aplicação.
    """
    import app.main as main_module

    assert "strict-transport-security" not in client.get("/health").headers

    monkeypatch.setattr(main_module.settings, "environment", "production")
    response = client.get("/health")
    assert response.headers["strict-transport-security"] == "max-age=63072000; includeSubDomains"
