"""account_deleted no enum nativo auditaction

Decisão de exclusão de conta revertida (2026-09-22): a decisão
anterior, registrada em `account_service` na ETAPA 25, era exclusão
sempre soft (`User.is_active`/`deactivated_at`), com apagamento físico
deliberadamente adiado pra um job de expurgo futuro, sem prazo de
retenção ainda definido. Essa decisão foi revertida a pedido do
usuário: contas de teste acumuladas durante QA precisavam de limpeza
de verdade (soft delete não libera o e-mail pra reuso nem reduz dado
no banco), e pra uma conta real também faz mais sentido, numa app que
lida com dado de saúde mental, oferecer exclusão definitiva de
verdade em vez de só desativação. `ACCOUNT_DELETION_REQUESTED`
continua no enum (não é removido — Postgres não permite remover valor
de enum sem recriar o tipo, mesmo padrão já documentado na migration
8a3f2c9b1e07), só que sem uso ativo daqui pra frente; `ACCOUNT_DELETED`
é o valor novo, gravado no exato commit que apaga a conta (ver
`account_service.delete_account`).

Mesmo padrão de `autocommit_block()` + `IF NOT EXISTS` já usado em
8a3f2c9b1e07 pra `ALTER TYPE ... ADD VALUE`.

Revision ID: c1a4e9f2b3d6
Revises: 8a3f2c9b1e07
Create Date: 2026-09-22T18:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c1a4e9f2b3d6'
down_revision = '8a3f2c9b1e07'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'ACCOUNT_DELETED'")


def downgrade() -> None:
    # Mesmo raciocínio já documentado em 8a3f2c9b1e07: Postgres não
    # permite remover um valor de enum sem recriar o tipo inteiro e
    # todas as colunas que o usam — no-op deliberado, não esquecimento.
    pass
