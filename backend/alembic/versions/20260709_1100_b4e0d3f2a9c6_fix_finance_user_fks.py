"""fix_finance_user_fks

Revision ID: b4e0d3f2a9c6
Revises: a3f9c2d1e8b7
Create Date: 2026-07-09 11:00:00.000000

Summary
-------
finance_journal_vouchers.created_by, finance_expense_claims.user_id, and
finance_ai_copilot_logs.user_id were constrained to user_profiles.id, but
every endpoint that populates them (finance_core.py create_journal_voucher,
finance_phase2.py create_expense_claim, finance_phase5.py cfo_copilot_chat)
assigns request.state.user_id, which is the JWT `sub` claim - i.e.
user_accounts.id (see the tenant_audit_logs fix in a3f9c2d1e8b7 for the
same class of bug). Retarget these FKs to match actual usage.

approved_by columns on these same tables are left pointing at
user_profiles.id: no endpoint currently populates them, so there is no
live mismatch to fix.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b4e0d3f2a9c6'
down_revision = 'a3f9c2d1e8b7'
branch_labels = None
depends_on = None

_CHANGES = [
    ("finance_journal_vouchers", "created_by", "finance_journal_vouchers_created_by_fkey", "SET NULL"),
    ("finance_expense_claims", "user_id", "finance_expense_claims_user_id_fkey", "CASCADE"),
    ("finance_ai_copilot_logs", "user_id", "finance_ai_copilot_logs_user_id_fkey", "CASCADE"),
]


def upgrade() -> None:
    for table, column, fk_name, ondelete in _CHANGES:
        op.drop_constraint(fk_name, table, schema='public', type_='foreignkey')
        op.create_foreign_key(
            fk_name, table, 'user_accounts', [column], ['id'],
            source_schema='public', referent_schema='public', ondelete=ondelete,
        )


def downgrade() -> None:
    for table, column, fk_name, ondelete in _CHANGES:
        op.drop_constraint(fk_name, table, schema='public', type_='foreignkey')
        op.create_foreign_key(
            fk_name, table, 'user_profiles', [column], ['id'],
            source_schema='public', referent_schema='public', ondelete=ondelete,
        )
