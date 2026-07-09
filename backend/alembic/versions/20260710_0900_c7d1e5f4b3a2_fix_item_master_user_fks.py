"""fix_item_master_user_fks

Revision ID: c7d1e5f4b3a2
Revises: b4e0d3f2a9c6
Create Date: 2026-07-10 09:00:00.000000

Summary
-------
universal_item_master.created_by/updated_by were constrained to
user_profiles.id, but the create_item/update_item endpoints populate them
from the JWT-verified user_id (user_accounts.id) via UserIDDep - same class
of bug as tenant_audit_logs (a3f9c2d1e8b7) and the finance tables
(b4e0d3f2a9c6). Every item create/update failed with
ForeignKeyViolationError (surfaced as a 400/500).

Separately, UserIDDep itself was fixed from a spoofable client-supplied
X-User-ID header to the JWT-verified request.state.user_id (see
app/middleware/tenant_auth.py get_verified_user_id) - no schema change
needed for that part, just retargeting these two FKs to match.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c7d1e5f4b3a2'
down_revision = 'b4e0d3f2a9c6'
branch_labels = None
depends_on = None

_COLUMNS = ["created_by", "updated_by"]


def upgrade() -> None:
    for column in _COLUMNS:
        fk_name = f"universal_item_master_{column}_fkey"
        op.drop_constraint(fk_name, "universal_item_master", schema='public', type_='foreignkey')
        op.create_foreign_key(
            fk_name, "universal_item_master", "user_accounts", [column], ["id"],
            source_schema='public', referent_schema='public', ondelete="SET NULL",
        )


def downgrade() -> None:
    for column in _COLUMNS:
        fk_name = f"universal_item_master_{column}_fkey"
        op.drop_constraint(fk_name, "universal_item_master", schema='public', type_='foreignkey')
        op.create_foreign_key(
            fk_name, "universal_item_master", "user_profiles", [column], ["id"],
            source_schema='public', referent_schema='public', ondelete="SET NULL",
        )
