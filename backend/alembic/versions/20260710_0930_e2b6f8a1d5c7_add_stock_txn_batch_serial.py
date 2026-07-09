"""add_stock_txn_batch_serial

Revision ID: e2b6f8a1d5c7
Revises: d8f2a6c9e1b4
Create Date: 2026-07-10 09:30:00.000000

Summary
-------
StockMovementRequest has always accepted batch_id and serial_numbers
(consumed by the Phase 4 batch/serial tracking logic in
crud/universal_warehousing.py execute_stock_movement), but
universal_stock_transactions never had matching columns. Since the
transaction record is built via
`UniversalStockTransaction(**payload.model_dump(by_alias=True))`, every
single stock movement - not just batch/serial ones - crashed with
`TypeError: 'batch_id' is an invalid keyword argument`, because the dict
always includes these keys (as None) even when unset.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e2b6f8a1d5c7'
down_revision = 'd8f2a6c9e1b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'universal_stock_transactions',
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='public',
    )
    op.add_column(
        'universal_stock_transactions',
        sa.Column('serial_numbers', postgresql.ARRAY(sa.Text()), nullable=True),
        schema='public',
    )
    op.create_foreign_key(
        'universal_stock_transactions_batch_id_fkey', 'universal_stock_transactions', 'universal_batch_master',
        ['batch_id'], ['id'], source_schema='public', referent_schema='public', ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('universal_stock_transactions_batch_id_fkey', 'universal_stock_transactions', schema='public', type_='foreignkey')
    op.drop_column('universal_stock_transactions', 'serial_numbers', schema='public')
    op.drop_column('universal_stock_transactions', 'batch_id', schema='public')
