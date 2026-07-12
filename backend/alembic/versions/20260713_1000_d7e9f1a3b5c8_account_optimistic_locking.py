"""account_optimistic_locking

Revision ID: d7e9f1a3b5c8
Revises: c6d8e0f2a4b7
Create Date: 2026-07-13 10:00:00.000000

Summary
-------
No optimistic-locking (version column) existed on any frequently-edited
document (audit #36) — two concurrent PATCH /accounts/{id} calls would
silently last-write-win, one edit clobbering the other with no warning.

Adds finance_accounts.version (default 1), checked by
crud_finance_core.update_account against the new optional
AccountUpdate.expected_version field. Scoped to Account (Chart of
Accounts) as the concrete implementation of this pattern — the audit's
named examples (invoices, orders, journal vouchers) don't currently have
real update endpoints to protect (journal vouchers by design, immutable
once posted per Sprint 1; invoices/orders as a separate, pre-existing gap
this migration doesn't address). Extending to other editable documents
follows the same column + optional expected_version-field pattern.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd7e9f1a3b5c8'
down_revision = 'c6d8e0f2a4b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'finance_accounts',
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text('1')),
    )


def downgrade() -> None:
    op.drop_column('finance_accounts', 'version')
