"""
ETAPA 30-32 (revisão de segurança): garante que `Settings` recusa
subir com `ENVIRONMENT=production` e os defaults inseguros ainda no
lugar (segredo de JWT de exemplo, ou debug ligado). Antes desta etapa
isso só era um comentário avisando — nada impedia de verdade.

Não usa o fixture `client`/`db_session` de propósito: `Settings` é
testado isolado, sem precisar do Postgres, então esses testes rodam
mesmo sem banco disponível.
"""
import pytest

from app.core.config import Settings


def test_production_with_default_jwt_secret_is_rejected():
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(environment="production", jwt_secret_key="changeme-in-env-file-this-is-not-a-real-secret", debug=False)


def test_production_with_debug_enabled_is_rejected():
    with pytest.raises(ValueError, match="DEBUG"):
        Settings(environment="production", jwt_secret_key="uma-chave-de-verdade-bem-longa-e-aleatoria", debug=True)


def test_production_with_real_secret_and_debug_off_is_accepted():
    settings = Settings(
        environment="production", jwt_secret_key="uma-chave-de-verdade-bem-longa-e-aleatoria", debug=False
    )
    assert settings.environment == "production"


def test_development_with_default_jwt_secret_is_still_allowed():
    """
    O guard só se aplica a `environment=production` — dev/test
    continuam livres para usar o valor de fábrica. Passa
    `jwt_secret_key` explicitamente (em vez de omitir) porque o
    `.env` local de desenvolvimento pode ter seu próprio valor
    configurado, o que tornaria este teste dependente de como a
    máquina de quem roda os testes está configurada.
    """
    settings = Settings(environment="development", jwt_secret_key="changeme-in-env-file-this-is-not-a-real-secret")
    assert settings.jwt_secret_key == "changeme-in-env-file-this-is-not-a-real-secret"
