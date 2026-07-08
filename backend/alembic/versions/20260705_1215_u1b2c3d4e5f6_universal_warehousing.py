"""universal_warehousing

Revision ID: u1b2c3d4e5f6
Revises: f7b8c9d0e1f2
Create Date: 2026-07-05 12:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'u1b2c3d4e5f6'
down_revision: Union[str, None] = 'f7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. universal_warehouses
    op.create_table(
        'universal_warehouses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization_branches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=64), server_default='main', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('manager_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_profiles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('capacity', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_univ_warehouse_tenant_code'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_warehouses_tenant_id'), 'universal_warehouses', ['tenant_id'], unique=False, schema='public')

    # 2. universal_warehouse_zones
    op.create_table(
        'universal_warehouse_zones',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'warehouse_id', 'code', name='uq_univ_zone_tenant_wh_code'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_warehouse_zones_tenant_id'), 'universal_warehouse_zones', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_warehouse_zones_warehouse_id'), 'universal_warehouse_zones', ['warehouse_id'], unique=False, schema='public')

    # 3. universal_warehouse_bins
    op.create_table(
        'universal_warehouse_bins',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouse_zones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('aisle', sa.String(length=64), nullable=True),
        sa.Column('rack', sa.String(length=64), nullable=True),
        sa.Column('shelf', sa.String(length=64), nullable=True),
        sa.Column('max_weight', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('max_volume', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'warehouse_id', 'code', name='uq_univ_bin_tenant_wh_code'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_warehouse_bins_tenant_id'), 'universal_warehouse_bins', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_warehouse_bins_warehouse_id'), 'universal_warehouse_bins', ['warehouse_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_warehouse_bins_zone_id'), 'universal_warehouse_bins', ['zone_id'], unique=False, schema='public')
    op.create_index('ix_univ_bin_metadata_gin', 'universal_warehouse_bins', ['metadata'], unique=False, schema='public', postgresql_using='gin')

    # 4. universal_stock_balance
    op.create_table(
        'universal_stock_balance',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_item_master.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('quantity_on_hand', sa.Numeric(precision=15, scale=4), server_default='0.0000', nullable=False),
        sa.Column('quantity_reserved', sa.Numeric(precision=15, scale=4), server_default='0.0000', nullable=False),
        sa.Column('quantity_allocated', sa.Numeric(precision=15, scale=4), server_default='0.0000', nullable=False),
        sa.Column('last_transaction_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('quantity_on_hand >= 0', name='chk_univ_stock_bal_non_negative'),
        sa.UniqueConstraint('tenant_id', 'item_id', 'warehouse_id', 'bin_id', name='uq_univ_stock_bal_composite'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_stock_balance_tenant_id'), 'universal_stock_balance', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_stock_balance_item_id'), 'universal_stock_balance', ['item_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_stock_balance_warehouse_id'), 'universal_stock_balance', ['warehouse_id'], unique=False, schema='public')

    # 5. universal_stock_transactions
    op.create_table(
        'universal_stock_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_item_master.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('transaction_type', sa.String(length=32), nullable=False),
        sa.Column('reference_type', sa.String(length=64), nullable=False),
        sa.Column('reference_id', sa.String(length=128), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_stock_transactions_tenant_id'), 'universal_stock_transactions', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_stock_transactions_item_id'), 'universal_stock_transactions', ['item_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_stock_transactions_warehouse_id'), 'universal_stock_transactions', ['warehouse_id'], unique=False, schema='public')
    op.create_index('ix_univ_stock_txn_metadata_gin', 'universal_stock_transactions', ['metadata'], unique=False, schema='public', postgresql_using='gin')

    # Enable RLS on all tables
    tables = [
        'universal_warehouses', 
        'universal_warehouse_zones', 
        'universal_warehouse_bins', 
        'universal_stock_balance', 
        'universal_stock_transactions'
    ]
    for tbl in tables:
        op.execute(f'ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;')
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_policy ON {tbl}
                USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
            """
        )

def downgrade() -> None:
    tables = [
        'universal_stock_transactions',
        'universal_stock_balance',
        'universal_warehouse_bins',
        'universal_warehouse_zones',
        'universal_warehouses'
    ]
    for tbl in tables:
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl};')
        op.drop_table(tbl, schema='public')
