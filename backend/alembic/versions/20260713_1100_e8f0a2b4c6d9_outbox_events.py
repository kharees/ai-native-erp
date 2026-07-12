"""outbox_events

Revision ID: e8f0a2b4c6d9
Revises: d7e9f1a3b5c8
Create Date: 2026-07-13 11:00:00.000000

Summary
-------
Transactional outbox foundation (audit #37) — see app/models/outbox.py
for the full rationale. Write side only; a relay/dispatcher that actually
publishes pending rows is separate, larger work not built here.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e8f0a2b4c6d9'
down_revision = 'd7e9f1a3b5c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'outbox_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(length=128), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_outbox_events_tenant_id', 'outbox_events', ['tenant_id'])
    op.create_index('ix_outbox_events_event_type', 'outbox_events', ['event_type'])
    op.create_index('ix_outbox_events_status', 'outbox_events', ['status'])


def downgrade() -> None:
    op.drop_index('ix_outbox_events_status', table_name='outbox_events')
    op.drop_index('ix_outbox_events_event_type', table_name='outbox_events')
    op.drop_index('ix_outbox_events_tenant_id', table_name='outbox_events')
    op.drop_table('outbox_events')
