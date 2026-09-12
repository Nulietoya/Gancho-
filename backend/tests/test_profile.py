"""
ETAPA 8 (perfil) + 9 (onboarding guiado). O onboarding aqui é
literalmente o preenchimento do perfil — não existe fluxo separado a
testar, então os cenários cobrem: criação única (1:1 com o usuário),
PATCH parcial não apaga campos não enviados, e conclusão idempotente.
"""
from tests.conftest import register_and_login as _register_and_login

OWNER_EMAIL = "perfil@example.com"
OWNER_PASSWORD = "senhaForte123"


def test_get_profile_before_creation_is_404(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.get("/api/v1/profile", headers=headers)
    assert response.status_code == 404


def test_create_profile(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.post(
        "/api/v1/profile",
        json={"display_name": "Nulie", "main_responsibilities": "cuidar da casa e do trabalho"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["display_name"] == "Nulie"
    assert body["tone_preference"] == "companheiro_calmo"
    assert body["timezone"] == "America/Sao_Paulo"
    assert body["onboarding_completed_at"] is None


def test_cannot_create_profile_twice(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/profile", json={"display_name": "Nulie"}, headers=headers)
    response = client.post("/api/v1/profile", json={"display_name": "Nulie de novo"}, headers=headers)
    assert response.status_code == 409


def test_patch_does_not_erase_unsent_fields(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post(
        "/api/v1/profile",
        json={"display_name": "Nulie", "habits": "acorda cedo", "work_or_study": "trabalho remoto"},
        headers=headers,
    )

    response = client.patch("/api/v1/profile", json={"habits": "acorda tarde agora"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["habits"] == "acorda tarde agora"
    assert body["work_or_study"] == "trabalho remoto"  # não foi enviado, não pode sumir
    assert body["display_name"] == "Nulie"


def test_patch_before_creation_is_404(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    response = client.patch("/api/v1/profile", json={"habits": "x"}, headers=headers)
    assert response.status_code == 404


def test_complete_onboarding_is_idempotent(client):
    headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/profile", json={"display_name": "Nulie"}, headers=headers)

    first = client.post("/api/v1/profile/complete-onboarding", headers=headers)
    assert first.status_code == 200
    completed_at = first.json()["onboarding_completed_at"]
    assert completed_at is not None

    second = client.post("/api/v1/profile/complete-onboarding", headers=headers)
    assert second.status_code == 200
    assert second.json()["onboarding_completed_at"] == completed_at


def test_profile_is_private_to_its_owner(client):
    """Cada usuário só enxerga (e edita) o próprio perfil — nunca por id de outrem."""
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/profile", json={"display_name": "Dono"}, headers=owner_headers)

    other_headers = _register_and_login(client, "outra@example.com", "outraSenhaForte123")
    response = client.get("/api/v1/profile", headers=other_headers)
    assert response.status_code == 404  # a pessoa "outra" não tem perfil próprio ainda

    body = client.get("/api/v1/profile", headers=owner_headers).json()
    assert body["display_name"] == "Dono"
