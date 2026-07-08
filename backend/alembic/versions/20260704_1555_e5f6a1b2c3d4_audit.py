"""
alembic/versions/20260704_1555_e5f6a1b2c3d4_audit.py
===================================================
Revision   : e5f6a1b2c3d4
Revises    : d4e5f6a1b2c3
Create Date: 2026-07-04 15:55:00.000000

Summary
-------
Phase 4 — Enterprise Audit & Activity Logging
Creates the tenant_audit_logs table with immutable properties and RLS.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e5f6a1b2c3d4'
down_revision = 'd4e5f6a1b2c3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('tenant_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action_category', sa.String(length=64), nullable=False),
        sa.Column('action_type', sa.String(length=64), nullable=False),
        sa.Column('action_source', sa.String(length=32), server_default=sa.text("'API'"), nullable=False),
        sa.Column('resource_id', sa.String(length=128), nullable=True),
        sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('correlation_id', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['public.user_profiles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_public_tenant_audit_logs_action_category'), 'tenant_audit_logs', ['action_category'], unique=False, schema='public')
    op.create_index(op.f('ix_public_tenant_audit_logs_action_type'), 'tenant_audit_logs', ['action_type'], unique=False, schema='public')
    op.create_index(op.f('ix_public_tenant_audit_logs_correlation_id'), 'tenant_audit_logs', ['correlation_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_tenant_audit_logs_created_at'), 'tenant_audit_logs', ['created_at'], unique=False, schema='public')
    op.create_index(op.f('ix_public_tenant_audit_logs_resource_id'), 'tenant_audit_logs', ['resource_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_tenant_audit_logs_tenant_id'), 'tenant_audit_logs', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_tenant_audit_logs_user_id'), 'tenant_audit_logs', ['user_id'], unique=False, schema='public')

    # Enable RLS
    op.execute("""
        ALTER TABLE public.tenant_audit_logs ENABLE ROW LEVEL SECURITY;

        CREATE POLICY "Tenant Isolation - tenant_audit_logs"
        ON public.tenant_audit_logs
        FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));
    """)

def downgrade() -> None:
    pass
