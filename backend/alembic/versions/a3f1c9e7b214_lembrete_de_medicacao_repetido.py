"""medicamentos: lembrete repetido para dificuldade de percepcao de tempo

Revision ID: a3f1c9e7b214
Revises: 65fb648a26f3
Create Date: 2026-09-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f1c9e7b214'
down_revision = '65fb648a26f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default só para preencher linhas já existentes (é uma
    # migration incremental de verdade, não a edição direta da
    # migration-base usada durante o desenvolvimento inicial do MVP,
    # ver docs/decisions.md); removido em seguida — o default de
    # verdade é o do model (`Medication.reminder_repeat_enabled`),
    # nunca o do schema.
    op.add_column(
        'medications',
        sa.Column('reminder_repeat_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.alter_column('medications', 'reminder_repeat_enabled', server_default=None)


def downgrade() -> None:
    op.drop_column('medications', 'reminder_repeat_enabled')
