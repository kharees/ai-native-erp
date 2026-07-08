"""universal_tracking

Revision ID: u3d4e5f6a1b2
Revises: u2c3d4e5f6a1
Create Date: 2026-07-05 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'u3d4e5f6a1b2'
down_revision: Union[str, None] = 'u2c3d4e5f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. universal_batch_master
    op.create_table(
        'universal_batch_master',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_item_master.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_number', sa.String(length=128), nullable=False),
        sa.Column('mfg_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('shelf_life_days', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('cost_multiplier', sa.Numeric(precision=5, scale=4), server_default='1.0000', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'item_id', 'batch_number', name='uq_univ_batch_tenant_item_batch'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_batch_master_tenant_id'), 'universal_batch_master', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_batch_master_item_id'), 'universal_batch_master', ['item_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_batch_master_expiry_date'), 'universal_batch_master', ['expiry_date'], unique=False, schema='public')

    # 2. universal_batch_stock
    op.create_table(
        'universal_batch_stock',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_batch_master.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('quantity_on_hand', sa.Numeric(precision=15, scale=4), server_default='0.0000', nullable=False),
        sa.Column('last_transaction_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('quantity_on_hand >= 0', name='chk_univ_batch_stock_non_negative'),
        sa.UniqueConstraint('tenant_id', 'batch_id', 'warehouse_id', 'bin_id', name='uq_univ_batch_stock_composite'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_batch_stock_tenant_id'), 'universal_batch_stock', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_batch_stock_batch_id'), 'universal_batch_stock', ['batch_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_batch_stock_warehouse_id'), 'universal_batch_stock', ['warehouse_id'], unique=False, schema='public')

    # 3. universal_serial_master
    op.create_table(
        'universal_serial_master',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_item_master.id', ondelete='CASCADE'), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_batch_master.id', ondelete='SET NULL'), nullable=True),
        sa.Column('serial_number', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='available', nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('bin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('warranty_expiry', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'item_id', 'serial_number', name='uq_univ_serial_tenant_item_serial'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_serial_master_tenant_id'), 'universal_serial_master', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_serial_master_item_id'), 'universal_serial_master', ['item_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_serial_master_batch_id'), 'universal_serial_master', ['batch_id'], unique=False, schema='public')

    # Enable RLS
    tables = ['universal_batch_master', 'universal_batch_stock', 'universal_serial_master']
    for tbl in tables:
        op.execute(f'ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;')
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_policy ON {tbl}
                USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
            """
        )

def downgrade() -> None:
    tables = ['universal_serial_master', 'universal_batch_stock', 'universal_batch_master']
    for tbl in tables:
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};')
        op.drop_table(tbl, schema='public')
