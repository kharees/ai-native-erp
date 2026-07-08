"""universal_ledger

Revision ID: u2c3d4e5f6a1
Revises: u1b2c3d4e5f6
Create Date: 2026-07-05 12:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'u2c3d4e5f6a1'
down_revision: Union[str, None] = 'u1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. universal_inventory_ledger
    op.create_table(
        'universal_inventory_ledger',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_item_master.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_warehouse_bins.id', ondelete='SET NULL'), nullable=True),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('universal_stock_transactions.id', ondelete='SET NULL'), nullable=True),
        
        sa.Column('quantity_before', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('movement_quantity', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('quantity_after', sa.Numeric(precision=15, scale=4), nullable=False),
        
        sa.Column('unit_cost', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=15, scale=2), server_default='0.0', nullable=False),
        
        sa.Column('reference_type', sa.String(length=64), nullable=False),
        sa.Column('reference_id', sa.String(length=128), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='public'
    )
    
    op.create_index(op.f('ix_public_universal_inventory_ledger_tenant_id'), 'universal_inventory_ledger', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_inventory_ledger_item_id'), 'universal_inventory_ledger', ['item_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_inventory_ledger_warehouse_id'), 'universal_inventory_ledger', ['warehouse_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_inventory_ledger_bin_id'), 'universal_inventory_ledger', ['bin_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_universal_inventory_ledger_transaction_id'), 'universal_inventory_ledger', ['transaction_id'], unique=False, schema='public')
    
    op.create_index('ix_univ_ledger_tenant_item_date', 'universal_inventory_ledger', ['tenant_id', 'item_id', 'created_at'], unique=False, schema='public')
    op.create_index('ix_univ_ledger_tenant_wh_date', 'universal_inventory_ledger', ['tenant_id', 'warehouse_id', 'created_at'], unique=False, schema='public')

    # Enable RLS
    op.execute('ALTER TABLE universal_inventory_ledger ENABLE ROW LEVEL SECURITY;')
    op.execute(
        """
        CREATE POLICY tenant_isolation_policy ON universal_inventory_ledger
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
        """
    )

def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS tenant_isolation_policy ON universal_inventory_ledger;')
    op.drop_table('universal_inventory_ledger', schema='public')
