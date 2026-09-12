"""
Dependencies compartilhadas pelas rotas. `get_current_user` é o
ponto único onde um JWT vira um usuário autenticado — toda rota
protegida depende dele direta ou indiretamente, então a lógica de
"o que torna um token válido" existe em um único lugar (item 36: a
resposta a "quem é" tem que ser sempre a mesma, em qualquer rota).
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import PermissionDenied, RelationshipNotFound
from app.core.security import JWTError, decode_access_token
from app.models.enums import PermissionKey
from app.models.trust import TrustedPersonRelationship
from app.models.user import User
from app.services import authorization_service

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="credenciais inválidas ou expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "access":
            raise unauthorized
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise unauthorized from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.deactivated_at is not None:
        raise unauthorized

    return user


def require_relationship_permission(permission_key: PermissionKey):
    """
    Dependency factory (ETAPA 7): protege uma rota exigindo que o
    usuário autenticado seja a pessoa de confiança de
    `relationship_id` (path param) E tenha `permission_key` concedida
    nesse relacionamento — em uma única checagem, sempre contra o
    estado atual do banco (nunca um claim de token).

    404 quando o relacionamento não existe para este usuário (não
    revela se existe para outra pessoa); 403 quando existe mas a
    permissão não está concedida ou o relacionamento não está ativo.
    """
    def dependency(
        relationship_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> TrustedPersonRelationship:
        try:
            return authorization_service.require_relationship_permission(
                db,
                relationship_id=relationship_id,
                trusted_user_id=current_user.id,
                permission_key=permission_key,
            )
        except RelationshipNotFound:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="relacionamento não encontrado")
        except PermissionDenied:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"permissão '{permission_key.value}' não concedida para este relacionamento",
            )

    return dependency


def require_active_relationship(
    relationship_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrustedPersonRelationship:
    """
    ETAPA 23/24 — variante de `require_relationship_permission` sem
    permissão obrigatória: garante só que o relacionamento existe,
    pertence a quem está autenticado como pessoa de confiança, e está
    ativo. Usada pelo dashboard da pessoa de confiança, onde cada seção
    da resposta checa a própria permissão que precisa (ver
    `dashboard_service.build_trusted_dashboard`) em vez de a rota
    inteira depender de uma permissão única.
    """
    try:
        return authorization_service.get_active_relationship_for_trusted_user(
            db, relationship_id=relationship_id, trusted_user_id=current_user.id
        )
    except RelationshipNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="relacionamento não encontrado")
