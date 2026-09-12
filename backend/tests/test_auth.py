"""
Testes da ETAPA 6 (autenticação). Batem na API via TestClient, não
direto no service — é o comportamento HTTP que o frontend vai
depender, então é isso que precisa estar certo.
"""
from app.services import auth_service

EMAIL = "nulie@example.com"
PASSWORD = "senhaForte123"


def register(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_register_creates_user(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == EMAIL
    assert "password" not in body and "password_hash" not in body


def test_register_rejects_duplicate_email(client):
    assert register(client).status_code == 201
    response = register(client)
    assert response.status_code == 409


def test_register_rejects_password_without_digit(client):
    response = register(client, password="somentesenhas")
    assert response.status_code == 422


def test_login_returns_token_pair_for_valid_credentials(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


def test_login_rejects_wrong_password(client):
    register(client)
    response = login(client, password="senhaErrada123")
    assert response.status_code == 401


def test_login_rejects_unknown_email_with_same_status_as_wrong_password(client):
    """Item 30 — não deve dar pra descobrir por essa rota se um e-mail está cadastrado."""
    response = login(client, email="ninguem@example.com")
    assert response.status_code == 401


def test_login_locks_account_after_max_failed_attempts(client):
    register(client)
    for _ in range(auth_service.MAX_FAILED_LOGIN_ATTEMPTS):
        assert login(client, password="senhaErrada123").status_code == 401

    locked_response = login(client, password=PASSWORD)  # até a senha certa é barrada
    assert locked_response.status_code == 423


def test_me_requires_valid_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token(client):
    register(client)
    tokens = login(client).json()

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_refresh_rotates_token_and_invalidates_the_old_one(client):
    register(client)
    tokens = login(client).json()

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_refresh_token = refreshed.json()["refresh_token"]
    assert new_refresh_token != tokens["refresh_token"]

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


def test_reusing_an_already_rotated_refresh_token_revokes_the_whole_session_family(client):
    """
    Reapresentar um refresh token já rotacionado (revogado) é tratado
    como possível roubo de sessão: em vez de só rejeitar aquele
    pedido, o serviço revoga TODAS as sessões ativas do usuário — até
    o token novo, recém-emitido pela própria rotação legítima, para de
    funcionar. Isso é o comportamento correto mesmo que pareça duro
    com o dono legítimo: ele só reusaria o token antigo por engano (ou
    porque uma cópia dele vazou), e nos dois casos forçar login de novo
    em todo dispositivo é mais seguro que deixar a sessão antiga viva.
    """
    register(client)
    tokens = login(client).json()

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    new_refresh_token = refreshed.json()["refresh_token"]

    # reusar o token antigo (já rotacionado) dispara a detecção
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401

    # o token novo, emitido pela rotação legítima segundos antes,
    # também foi revogado — a família inteira de sessão caiu junto
    new_token_after_reuse = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_refresh_token}
    )
    assert new_token_after_reuse.status_code == 401


def test_reusing_a_rotated_refresh_token_writes_audit_log(client, db_session):
    from app.models.audit import AuditLog
    from app.models.enums import AuditAction

    register(client)
    tokens = login(client).json()
    client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    entries = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == AuditAction.SUSPECTED_SESSION_THEFT)
        .all()
    )
    assert len(entries) == 1


def test_logout_revokes_refresh_token(client):
    register(client)
    tokens = login(client).json()

    logout_response = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout_response.status_code == 204

    refresh_after_logout = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_after_logout.status_code == 401


def test_change_password_requires_current_password(client):
    register(client)
    tokens = login(client).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    wrong = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "errada123", "new_password": "novaSenha123"},
        headers=headers,
    )
    assert wrong.status_code == 401


def test_change_password_succeeds_and_revokes_other_sessions(client):
    register(client)
    tokens = login(client).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    ok = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "novaSenha123"},
        headers=headers,
    )
    assert ok.status_code == 204

    # refresh token emitido antes da troca não pode mais funcionar
    old_refresh_still_works = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert old_refresh_still_works.status_code == 401

    # login com a senha nova funciona
    assert login(client, password="novaSenha123").status_code == 200
    # login com a senha antiga não funciona mais
    assert login(client, password=PASSWORD).status_code == 401


def test_password_reset_flow_end_to_end(client, db_session):
    register(client)

    accepted = client.post("/api/v1/auth/password-reset/request", json={"email": EMAIL})
    assert accepted.status_code == 202

    # o token em si é entregue por e-mail em produção (ainda não
    # conectado nesta etapa) — para o teste, geramos um novo como o
    # service faria, contra a mesma sessão transacional do teste.
    raw_token = auth_service.create_password_reset_token(db_session, EMAIL)
    assert raw_token is not None

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "outraSenhaNova123"},
    )
    assert confirm.status_code == 204

    assert login(client, password="outraSenhaNova123").status_code == 200
    assert login(client, password=PASSWORD).status_code == 401

    # o mesmo token não pode ser reaproveitado
    reuse = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "maisUmaSenha123"},
    )
    assert reuse.status_code == 400


def test_password_reset_request_for_unknown_email_still_returns_202(client):
    """Não pode vazar se o e-mail existe ou não (mesmo raciocínio do login)."""
    response = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "ninguem@example.com"}
    )
    assert response.status_code == 202
