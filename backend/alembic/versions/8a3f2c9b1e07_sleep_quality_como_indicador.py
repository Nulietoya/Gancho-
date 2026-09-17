"""sleep_quality como indicador (IndicatorKey)

Adiciona 'SLEEP_QUALITY' ao enum nativo `indicatorkey` do Postgres.
`sleep_quality` já existia como campo de `DailyCheckIn` desde a ETAPA
11 (escala 1-5), mas ficava fora do motor de baseline/desvio por
decisão de escopo registrada em `indicator_service` — sem ainda um
`IndicatorKey` correspondente. Corrigido agora: mapeado como indicador
próprio (não misturado com `SLEEP_HOURS`, que é outra unidade e outra
fonte — rotina/sensor, ainda sem dado real) e adicionado ao motor de
ESTABILIDADE, junto de adesão a medicação e humor, seguindo o mesmo
padrão já documentado no motor de desvio ("adicionar um sinal novo a
um motor é só acrescentar uma linha em ENGINE_INDICATORS").

`ALTER TYPE ... ADD VALUE` não pode rodar dentro da mesma transação
que outros comandos em versões antigas do Postgres, e o valor
adicionado não pode ser usado na mesma transação em que foi criado —
por isso o `autocommit_block()`, recomendado pelo próprio Alembic para
este caso. `IF NOT EXISTS` torna o upgrade idempotente. Postgres não
permite remover um valor de enum diretamente, então o downgrade é
deliberadamente um no-op documentado (mesmo raciocínio já registrado
noutras migrations do projeto: não inventar reversibilidade que o
banco não oferece) — o ciclo upgrade→downgrade→upgrade continua
seguro porque o upgrade é idempotente.

Revision ID: 8a3f2c9b1e07
Revises: 65fb648a26f3
Create Date: 2026-09-17 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '8a3f2c9b1e07'
down_revision = '65fb648a26f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE indicatorkey ADD VALUE IF NOT EXISTS 'SLEEP_QUALITY'")


def downgrade() -> None:
    # Postgres não suporta remover um valor de enum (sem recriar o tipo
    # inteiro e todas as colunas/índices que o usam) — decisão de escopo
    # registrada, não esquecimento. Reverter de verdade exigiria garantir
    # antes que nenhuma linha em uso use 'SLEEP_QUALITY', fora do alcance
    # de uma migration automática.
    pass
