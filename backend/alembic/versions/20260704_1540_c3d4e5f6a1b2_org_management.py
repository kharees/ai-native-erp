"""
alembic/versions/20260704_1540_c3d4e5f6a1b2_org_management.py
============================================================
Revision   : c3d4e5f6a1b2
Revises    : b2c3d4e5f6a1
Create Date: 2026-07-04 15:40:00.000000

Summary
-------
Phase 2 — Enterprise User & Organization Management
Adds organization models and user hierarchy fields.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a1b2'
down_revision = 'b2c3d4e5f6a1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Update tenants table
    op.add_column('tenants', sa.Column('company_info', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column('tenants', sa.Column('business_settings', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))

    # 2. Create tenant_branches
    op.create_table('tenant_branches',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('address', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_public_tenant_branches_tenant_id'), 'tenant_branches', ['tenant_id'], unique=False, schema='public')

    # 3. Create tenant_departments
    op.create_table('tenant_departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['public.tenant_departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_public_tenant_departments_tenant_id'), 'tenant_departments', ['tenant_id'], unique=False, schema='public')

    # 4. Create tenant_warehouses
    op.create_table('tenant_warehouses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('address', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['branch_id'], ['public.tenant_branches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_public_tenant_warehouses_tenant_id'), 'tenant_warehouses', ['tenant_id'], unique=False, schema='public')

    # 5. Update user_profiles
    op.add_column('user_profiles', sa.Column('employee_code', sa.String(length=64), nullable=True), schema='public')
    op.add_column('user_profiles', sa.Column('status', sa.String(length=32), server_default=sa.text("'Active'"), nullable=False), schema='public')
    op.add_column('user_profiles', sa.Column('designation', sa.String(length=128), nullable=True), schema='public')
    op.add_column('user_profiles', sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True), schema='public')
    op.add_column('user_profiles', sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=True), schema='public')
    op.add_column('user_profiles', sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=True), schema='public')
    op.add_column('user_profiles', sa.Column('manager_id', postgresql.UUID(as_uuid=True), nullable=True), schema='public')
    op.add_column('user_profiles', sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False), schema='public')
    
    op.create_index(op.f('ix_public_user_profiles_employee_code'), 'user_profiles', ['employee_code'], unique=False, schema='public')
    op.create_foreign_key(None, 'user_profiles', 'tenant_branches', ['branch_id'], ['id'], source_schema='public', referent_schema='public', ondelete='SET NULL')
    op.create_foreign_key(None, 'user_profiles', 'tenant_departments', ['department_id'], ['id'], source_schema='public', referent_schema='public', ondelete='SET NULL')
    op.create_foreign_key(None, 'user_profiles', 'user_profiles', ['manager_id'], ['id'], source_schema='public', referent_schema='public', ondelete='SET NULL')
    op.create_foreign_key(None, 'user_profiles', 'tenant_warehouses', ['warehouse_id'], ['id'], source_schema='public', referent_schema='public', ondelete='SET NULL')

    # 6. Apply RLS Policies to New Tables
    op.execute("""
        ALTER TABLE public.tenant_branches ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.tenant_departments ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.tenant_warehouses ENABLE ROW LEVEL SECURITY;

        CREATE POLICY "Tenant Isolation - tenant_branches"
        ON public.tenant_branches
        FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));

        CREATE POLICY "Tenant Isolation - tenant_departments"
        ON public.tenant_departments
        FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));

        CREATE POLICY "Tenant Isolation - tenant_warehouses"
        ON public.tenant_warehouses
        FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));
    """)

def downgrade() -> None:
    pass
