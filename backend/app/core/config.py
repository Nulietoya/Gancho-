"""
Configuração central da aplicação.

Tudo que muda entre ambientes (dev / test / produção) vem daqui,
lido de variáveis de ambiente. Nunca hardcode segredo ou string de
conexão em outro lugar do código.
"""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valor de fábrica de `jwt_secret_key` — nunca deve chegar num ambiente
# de produção real. Extraído pra constante pra que o guard de startup
# abaixo e o valor default do campo nunca possam divergir por engano.
_INSECURE_DEFAULT_JWT_SECRET = "changeme-in-env-file-this-is-not-a-real-secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Identidade / ambiente
    app_name: str = "Gancho API"
    environment: str = "development"  # development | test | production
    debug: bool = True

    # Banco de dados
    database_url: str = "postgresql+psycopg2://gancho:gancho@localhost:5432/gancho"

    # Autenticação (JWT)
    # Em produção, jwt_secret_key DEVE vir de uma variável de ambiente real,
    # nunca do valor default abaixo.
    jwt_secret_key: str = _INSECURE_DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # CORS (origens do frontend autorizadas)
    cors_origins: list[str] = ["http://localhost:5173"]

    # E-mail (ETAPA 22). Sem `smtp_host` configurado, o envio cai no
    # backend de log (ver app/core/email.py) — nunca falha por falta
    # de provedor, só não entrega de verdade; configurar estas
    # variáveis em produção liga o envio real sem mudar código nenhum
    # de quem chama `send_email`.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True

    # Usado só para montar o link dentro do corpo do e-mail de reset
    # de senha (ainda não existe frontend publicado).
    frontend_url: str = "http://localhost:5173"

    @model_validator(mode="after")
    def _guard_against_insecure_production_config(self) -> "Settings":
        """
        ETAPA 30-32 (revisão de segurança): até aqui, os comentários
        acima avisavam que produção precisa sobrescrever
        `jwt_secret_key`/`debug`, mas nada IMPEDIA subir com os
        defaults inseguros — um `ENVIRONMENT=production` no `.env` sem
        as outras variáveis simplesmente funcionaria, silenciosamente,
        com o segredo de JWT público (está neste arquivo, versionado)
        e com `debug=True` (que costuma vazar stack trace em resposta
        de erro). Isso vira erro de inicialização em vez de aviso em
        comentário: falha rápido e alto, antes de aceitar uma única
        requisição, em vez de rodar "funcionando" de um jeito inseguro.
        """
        if self.environment == "production":
            if self.jwt_secret_key == _INSECURE_DEFAULT_JWT_SECRET:
                raise ValueError(
                    "ENVIRONMENT=production com JWT_SECRET_KEY ainda no valor "
                    "default e inseguro — defina uma chave real (ex.: "
                    "`python -c \"import secrets; print(secrets.token_urlsafe(64))\"`) "
                    "na variável de ambiente JWT_SECRET_KEY antes de subir."
                )
            if self.debug:
                raise ValueError(
                    "ENVIRONMENT=production com DEBUG=true — isso pode vazar "
                    "detalhes internos (stack trace, etc.) em respostas de erro. "
                    "Defina DEBUG=false na variável de ambiente antes de subir."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
