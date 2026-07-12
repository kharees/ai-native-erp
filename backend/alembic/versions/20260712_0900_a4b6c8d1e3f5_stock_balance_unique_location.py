"""stock_balance_unique_location

Revision ID: a4b6c8d1e3f5
Revises: f9a3c5e7b2d4
Create Date: 2026-07-12 09:00:00.000000

Summary
-------
execute_stock_movement()'s get-or-create for UniversalStockBalance ran a
SELECT ... FOR UPDATE that locks nothing when no row matches, then
unconditionally INSERTed a new balance row if none was found. Two
concurrent first-movements for the same (tenant_id, item_id, warehouse_id,
bin_id) location both raced past the SELECT, both found no row, and both
inserted — creating two balance rows for the same location that silently
diverge from then on, with nothing at the DB layer to prevent it.

Adds two partial unique indexes (rather than one plain composite unique
constraint) because bin_id is nullable and Postgres treats NULL as
distinct from itself in a regular UNIQUE constraint — a plain constraint
would still allow unlimited duplicate rows for any bin-less location.
One index covers bin_id IS NOT NULL, the other bin_id IS NULL.

Paired with an application change to execute_stock_movement() that now
does INSERT ... ON CONFLICT DO NOTHING against these indexes before the
SELECT ... FOR UPDATE, so the row is guaranteed to exist before it's
locked — closing the race completely rather than just detecting it.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a4b6c8d1e3f5'
down_revision = 'f9a3c5e7b2d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        'uq_stock_balance_location',
        'universal_stock_balance',
        ['tenant_id', 'item_id', 'warehouse_id', 'bin_id'],
        unique=True,
        postgresql_where=sa.text('bin_id IS NOT NULL'),
    )
    op.create_index(
        'uq_stock_balance_location_null_bin',
        'universal_stock_balance',
        ['tenant_id', 'item_id', 'warehouse_id'],
        unique=True,
        postgresql_where=sa.text('bin_id IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_stock_balance_location_null_bin', table_name='universal_stock_balance')
    op.drop_index('uq_stock_balance_location', table_name='universal_stock_balance')
