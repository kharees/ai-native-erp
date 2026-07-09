"""fix_audit_log_user_fk

Revision ID: a3f9c2d1e8b7
Revises: V002
Create Date: 2026-07-09 10:00:00.000000

Summary
-------
tenant_audit_logs.user_id was originally constrained to user_profiles.id,
but AuditLogger.log_action() and the JWT auth flow populate request.state.user_id
from the JWT `sub` claim, which is user_accounts.id (not user_profiles.id).
Retarget the FK to match actual usage.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a3f9c2d1e8b7'
down_revision = 'V002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        'tenant_audit_logs_user_id_fkey',
        'tenant_audit_logs',
        schema='public',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'tenant_audit_logs_user_id_fkey',
        'tenant_audit_logs',
        'user_accounts',
        ['user_id'],
        ['id'],
        source_schema='public',
        referent_schema='public',
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'tenant_audit_logs_user_id_fkey',
        'tenant_audit_logs',
        schema='public',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'tenant_audit_logs_user_id_fkey',
        'tenant_audit_logs',
        'user_profiles',
        ['user_id'],
        ['id'],
        source_schema='public',
        referent_schema='public',
        ondelete='SET NULL',
    )
