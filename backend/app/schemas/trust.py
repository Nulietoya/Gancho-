import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import ObservationCategory, ObservationIntensity, ObservationSince, PermissionKey, RelationshipStatus


class InviteRequest(BaseModel):
    email: EmailStr
    relationship_label: str | None = Field(default=None, max_length=80)


class AcceptInviteRequest(BaseModel):
    invite_token: str


class PermissionPublic(BaseModel):
    permission_key: PermissionKey
    is_granted: bool
    indicator_scope: list[str] | None = None
    granted_at: datetime | None = None
    revoked_at: datetime | None = None

    model_config = {"from_attributes": True}


class RelationshipPublic(BaseModel):
    id: uuid.UUID
    invite_email: EmailStr
    relationship_label: str | None
    status: RelationshipStatus
    invited_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    permissions: list[PermissionPublic] = []

    model_config = {"from_attributes": True}


class InviteCreatedResponse(RelationshipPublic):
    """
    Resposta de `POST /trusted-people/invite`, só nesse endpoint —
    inclui `invite_token`, que `RelationshipPublic` (usado em
    `GET /trusted-people` e em toda outra resposta de relacionamento)
    deliberadamente não expõe.

    Bug real corrigido aqui: até então, o código do convite era gerado
    e gravado no banco, mas nunca saía dali — nem por e-mail (a chamada
    pra enviar nunca existiu em `trust_service.invite_trusted_person`),
    nem devolvido nesta resposta pra a pessoa dona da conta copiar e
    mandar na mão. Resultado: nenhuma forma, automática ou manual, do
    convite chegar a quem foi convidado. Ver docs/decisions.md.
    """

    invite_token: str


class RelationshipAsTrustedPublic(RelationshipPublic):
    """
    ETAPA 27 (6ª leva): mesma forma de `RelationshipPublic`, do ponto de
    vista de quem é a PESSOA DE CONFIANÇA, não o dono — usada em
    `GET /trusted-people/watching`. Acrescenta `owner_display_name`
    porque `invite_email` neste schema é o e-mail de quem foi
    convidado (a própria pessoa de confiança), não identifica o dono.
    Vem do `Profile.display_name` do dono quando o onboarding já foi
    feito; cai de volta pro e-mail da conta do dono quando ainda não.
    """

    owner_display_name: str


class PermissionUpdate(BaseModel):
    permission_key: PermissionKey
    is_granted: bool
    indicator_scope: list[str] | None = None


class PermissionsUpdateRequest(BaseModel):
    permissions: list[PermissionUpdate] = Field(min_length=1)


class ObservationCreate(BaseModel):
    category: ObservationCategory
    since: ObservationSince
    intensity: ObservationIntensity
    note: str | None = Field(default=None, max_length=500)


class ObservationPublic(BaseModel):
    id: uuid.UUID
    relationship_id: uuid.UUID
    category: ObservationCategory
    since: ObservationSince
    intensity: ObservationIntensity
    note: str | None
    recorded_at: datetime

    model_config = {"from_attributes": True}
