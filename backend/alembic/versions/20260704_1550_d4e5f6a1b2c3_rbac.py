"""
alembic/versions/20260704_1550_d4e5f6a1b2c3_rbac.py
===================================================
Revision   : d4e5f6a1b2c3
Revises    : c3d4e5f6a1b2
Create Date: 2026-07-04 15:50:00.000000

Summary
-------
Phase 3 — Enterprise RBAC Implementation
Adds roles, permissions, and assignment junction tables.
Seeds system roles.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'd4e5f6a1b2c3'
down_revision = 'c3d4e5f6a1b2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create tenant_roles
    roles_table = op.create_table('tenant_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('hierarchy_level', sa.Integer(), server_default=sa.text('100'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='uix_tenant_role_name'),
        schema='public'
    )
    op.create_index(op.f('ix_public_tenant_roles_tenant_id'), 'tenant_roles', ['tenant_id'], unique=False, schema='public')

    # 2. Create tenant_permissions
    permissions_table = op.create_table('tenant_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('module', sa.String(length=64), nullable=False),
        sa.Column('feature', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('module', 'feature', 'action', name='uix_permission_def'),
        schema='public'
    )
    op.create_index(op.f('ix_public_tenant_permissions_feature'), 'tenant_permissions', ['feature'], unique=False, schema='public')
    op.create_index(op.f('ix_public_tenant_permissions_module'), 'tenant_permissions', ['module'], unique=False, schema='public')

    # 3. Create tenant_role_permissions
    op.create_table('tenant_role_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['public.tenant_permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['public.tenant_roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uix_role_permission'),
        schema='public'
    )
    op.create_index(op.f('ix_public_tenant_role_permissions_role_id'), 'tenant_role_permissions', ['role_id'], unique=False, schema='public')

    # 4. Create tenant_user_roles
    op.create_table('tenant_user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['branch_id'], ['public.tenant_branches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['public.tenant_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['public.user_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['public.tenant_warehouses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', 'branch_id', 'warehouse_id', name='uix_user_role_scope'),
        schema='public'
    )
    op.create_index(op.f('ix_public_tenant_user_roles_tenant_id'), 'tenant_user_roles', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_tenant_user_roles_user_id'), 'tenant_user_roles', ['user_id'], unique=False, schema='public')

    # 5. Enable RLS
    op.execute("""
        ALTER TABLE public.tenant_roles ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.tenant_user_roles ENABLE ROW LEVEL SECURITY;

        -- Roles policy: allows reading system roles (tenant_id IS NULL) OR roles for the specific tenant
        CREATE POLICY "Tenant Isolation - tenant_roles"
        ON public.tenant_roles
        FOR ALL USING (
            tenant_id IS NULL OR 
            tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid())
        );

        CREATE POLICY "Tenant Isolation - tenant_user_roles"
        ON public.tenant_user_roles
        FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));
    """)

    # 6. Seed Default System Roles
    # The default system roles do not have a tenant_id (NULL)
    default_roles = [
        {'id': str(uuid.uuid4()), 'name': 'Super Admin', 'hierarchy_level': 1, 'is_system': True},
        {'id': str(uuid.uuid4()), 'name': 'Organization Admin', 'hierarchy_level': 10, 'is_system': True},
        {'id': str(uuid.uuid4()), 'name': 'Branch Manager', 'hierarchy_level': 20, 'is_system': True},
        {'id': str(uuid.uuid4()), 'name': 'Finance Manager', 'hierarchy_level': 30, 'is_system': True},
        {'id': str(uuid.uuid4()), 'name': 'Accountant', 'hierarchy_level': 40, 'is_system': True},
        {'id': str(uuid.uuid4()), 'name': 'Sales Manager', 'hierarchy_level': 50, 'is_system': True},
        {'id': str(uuid.uuid4()), 'name': 'Sales Executive', 'hierarchy_level': 60, 'is_system': True},
        {'id': str(uuid.uuid4()), 'name': 'Inventory Manager', 'hierarchy_level': 70, 'is_system': True},
        {'id': str(uuid.uuid4()), 'name': 'Warehouse Staff', 'hierarchy_level': 80, 'is_system': True},
        {'id': str(uuid.uuid4()), 'name': 'HR Manager', 'hierarchy_level': 90, 'is_system': True},
        {'id': str(uuid.uuid4()), 'name': 'Viewer', 'hierarchy_level': 999, 'is_system': True},
    ]
    
    op.bulk_insert(roles_table, default_roles)

def downgrade() -> None:
    pass
