"""idempotency_keys

Revision ID: b5c7d9e2f4a6
Revises: a4b6c8d1e3f5
Create Date: 2026-07-12 10:00:00.000000

Summary
-------
Adds the idempotency_keys table backing an `Idempotency-Key` header on
payment receipt / refund and tax / proforma invoice creation. A POS or
mobile client retrying a timed-out create request with no idempotency
support double-charges or double-invoices; this lets it safely retry with
the same key and get the original response back instead of a duplicate.

Claiming a key is a single INSERT protected by the unique constraint on
(tenant_id, endpoint, key) — see app/models/idempotency.py for the
concurrency reasoning and app/services/idempotency.py for how it's used.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b5c7d9e2f4a6'
down_revision = 'a4b6c8d1e3f5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'idempotency_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('endpoint', sa.String(length=128), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('response_body', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'endpoint', 'key', name='uq_idempotency_tenant_endpoint_key'),
    )
    op.create_index('ix_idempotency_keys_tenant_id', 'idempotency_keys', ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_idempotency_keys_tenant_id', table_name='idempotency_keys')
    op.drop_table('idempotency_keys')
