"""
Primitivas de segurança usadas pelo módulo de autenticação.

Duas famílias de "token" convivem aqui de propósito:

- **Access token (JWT)**: curto (15 min por padrão), assinado,
  stateless — a API decodifica e confia sem consultar o banco a cada
  requisição. Rápido, mas não é revogável antes de expirar sozinho.
- **Refresh token / reset token (opaco, aleatório)**: guardado
  (hasheado) no banco em `RefreshSession`/`PasswordResetToken` — é o
  que permite revogação de verdade (logout, troca de senha, token de
  reset usado uma vez). Nunca é um JWT: não precisa carregar claim
  nenhuma, só precisa ser imprevisível e checável contra o banco.
"""
import hashlib
import secrets
from datetime import timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.time import utc_now

settings = get_settings()

# Argon2: vencedor da Password Hashing Competition, projetado
# especificamente para resistir a ataque por GPU/ASIC — a escolha
# correta para hash de senha humana (baixa entropia). Diferente do
# hash usado para os tokens opacos abaixo (ver docstring do módulo).
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str) -> str:
    now = utc_now()
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "iat": now, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Levanta jose.JWTError se inválido, expirado ou malformado."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def generate_opaque_token() -> str:
    """Token de alta entropia para refresh/reset — nunca um JWT (ver docstring do módulo)."""
    return secrets.token_urlsafe(48)


def hash_opaque_token(raw_token: str) -> str:
    """
    SHA-256 é suficiente aqui: o token já tem ~64 bits de entropia
    por bloco de token_urlsafe(48) — muito acima do que uma senha
    humana tem. Usar Argon2 (lento por design) para isso só custaria
    CPU sem ganho de segurança real.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


__all__ = [
    "JWTError",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "generate_opaque_token",
    "hash_opaque_token",
]
