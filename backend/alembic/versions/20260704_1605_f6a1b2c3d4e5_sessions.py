"""
alembic/versions/20260704_1605_f6a1b2c3d4e5_sessions.py
======================================================
Revision   : f6a1b2c3d4e5
Revises    : e5f6a1b2c3d4
Create Date: 2026-07-04 16:05:00.000000

Summary
-------
Phase 5 — Enterprise Session & Device Management
Creates tenant_sessions and tenant_devices tables with RLS.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f6a1b2c3d4e5'
down_revision = 'e5f6a1b2c3d4'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create tenant_sessions
    op.create_table('tenant_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('browser', sa.String(length=64), nullable=True),
        sa.Column('os', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('TRUE'), nullable=False),
        sa.Column('last_active_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['public.user_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_public_tenant_sessions_tenant_id'), 'tenant_sessions', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_tenant_sessions_user_id'), 'tenant_sessions', ['user_id'], unique=False, schema='public')

    # 2. Create tenant_devices
    op.create_table('tenant_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=False),
        sa.Column('browser', sa.String(length=64), nullable=True),
        sa.Column('os', sa.String(length=64), nullable=True),
        sa.Column('last_ip_address', sa.String(length=64), nullable=True),
        sa.Column('is_trusted', sa.Boolean(), server_default=sa.text('FALSE'), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['public.tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['public.user_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'device_fingerprint', name='uix_user_device'),
        schema='public'
    )
    op.create_index(op.f('ix_public_tenant_devices_tenant_id'), 'tenant_devices', ['tenant_id'], unique=False, schema='public')
    op.create_index(op.f('ix_public_tenant_devices_user_id'), 'tenant_devices', ['user_id'], unique=False, schema='public')

    # 3. Enable RLS
    op.execute("""
        ALTER TABLE public.tenant_sessions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.tenant_devices ENABLE ROW LEVEL SECURITY;

        CREATE POLICY "Tenant Isolation - tenant_sessions"
        ON public.tenant_sessions
        FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));

        CREATE POLICY "Tenant Isolation - tenant_devices"
        ON public.tenant_devices
        FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));
    """)


def downgrade() -> None:
    pass
