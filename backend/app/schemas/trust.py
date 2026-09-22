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


class OwnerRelationshipPublic(RelationshipPublic):
    """
    Resposta de `GET /trusted-people` (lista do DONO da conta, nunca
    da pessoa de confiança). Traz `invite_token` de volta SÓ enquanto
    o convite está pendente — depois de aceito ou revogado o link não
    serve mais pra nada, então não há motivo pra continuar expondo o
    valor.

    Isso resolve uma lacuna real: antes, o token só aparecia na
    resposta do momento exato da criação do convite (`InviteCreatedResponse`)
    — se a pessoa saísse da tela ou desse F5 antes de copiar o link
    (ex.: o e-mail falhou e ela precisava reenviar na mão por outro
    canal), não tinha como recuperar aquele link de novo. Seguro
    reexpor aqui porque esta rota já é isolada por dono (cada um só
    vê os próprios relacionamentos) — nada muda pra quem NÃO é o
    dono: `RelationshipAsTrustedPublic` (usada em `/watching`) segue
    sem o campo.
    """

    invite_token: str | None = None


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


class InvitePreview(BaseModel):
    """
    Resposta de `GET /trusted-people/invite-preview/{token}` — a ÚNICA
    rota deste módulo que não exige login. Bug real encontrado em
    produção (ver docs/decisions.md): a pessoa convidada só descobria
    que o convite era pra outro e-mail depois de tentar aceitar (erro
    genérico 400) — muitas vezes já logada numa conta pessoal diferente
    da que o dono digitou, sem forma de saber isso antes de tentar.
    Esta rota deixa a página de aceite mostrar "convite de <dono> para
    <invite_email>" ANTES de pedir login, então quem abre o link já
    sabe com qual conta entrar (ou criar) antes de gastar uma tentativa.
    Não é vazamento: quem já tem o token (imprevisível, só sai da tela
    do dono ou do e-mail) já tinha acesso a este mesmo e-mail — esta
    rota só evita que a pessoa convidada descubra isso do jeito difícil.
    """

    invite_email: EmailStr
    owner_display_name: str
    status: RelationshipStatus


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
