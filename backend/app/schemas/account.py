"""ETAPA 25 (item 53) — schemas de ciclo de vida de conta."""
from pydantic import BaseModel, Field


class AccountDeleteRequest(BaseModel):
    password: str = Field(min_length=1)
