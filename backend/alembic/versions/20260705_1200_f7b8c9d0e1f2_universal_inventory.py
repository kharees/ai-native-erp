"""
alembic/versions/20260705_1200_f7b8c9d0e1f2_universal_inventory.py
===================================================================
Revision   : f7b8c9d0e1f2
Revises    : f6a1b2c3d4e5
Create Date: 2026-07-05 12:00:00.000000

Summary
-------
Phase 1 — Universal Dynamic Inventory Module
Creates universal_categories, universal_brands, universal_uoms, and universal_item_master tables.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f7b8c9d0e1f2'
down_revision = 'f6a1b2c3d4e5'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Categories
    op.create_table('universal_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('TRUE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['public.universal_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_categories_tenant_id'), 'universal_categories', ['tenant_id'], unique=False, schema='public')

    # 2. Brands
    op.create_table('universal_brands',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('logo_url', sa.String(length=1024), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('TRUE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_brands_tenant_id'), 'universal_brands', ['tenant_id'], unique=False, schema='public')

    # 3. UOMs
    op.create_table('universal_uoms',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('abbreviation', sa.String(length=32), nullable=False),
        sa.Column('base_uom_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('conversion_factor', sa.Numeric(precision=18, scale=6), server_default=sa.text('1.0'), nullable=False),
        sa.Column('decimal_precision', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('TRUE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['base_uom_id'], ['public.universal_uoms.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_uoms_tenant_id'), 'universal_uoms', ['tenant_id'], unique=False, schema='public')

    # 4. Item Master
    op.create_table('universal_item_master',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_code', sa.String(length=64), nullable=False),
        sa.Column('sku', sa.String(length=64), nullable=False),
        sa.Column('barcode', sa.String(length=128), nullable=True),
        sa.Column('qr_code', sa.String(length=128), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('short_name', sa.String(length=128), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'draft'"), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('TRUE'), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uom_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('images', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column('documents', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('variants', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['brand_id'], ['public.universal_brands.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['category_id'], ['public.universal_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['public.user_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uom_id'], ['public.universal_uoms.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['public.user_profiles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'item_code', name='uq_universal_item_tenant_code'),
        sa.UniqueConstraint('tenant_id', 'sku', name='uq_universal_item_tenant_sku'),
        schema='public'
    )
    op.create_index(op.f('ix_public_universal_item_master_tenant_id'), 'universal_item_master', ['tenant_id'], unique=False, schema='public')
    op.create_index('ix_universal_item_variants_gin', 'universal_item_master', ['variants'], unique=False, schema='public', postgresql_using='gin')
    op.create_index('ix_universal_item_attributes_gin', 'universal_item_master', ['attributes'], unique=False, schema='public', postgresql_using='gin')

    # Enable RLS on all tables
    for tbl in ['universal_categories', 'universal_brands', 'universal_uoms', 'universal_item_master']:
        op.execute(f"ALTER TABLE public.{tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY "Tenant Isolation - {tbl}"
            ON public.{tbl}
            FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));
        """)

def downgrade() -> None:
    pass
