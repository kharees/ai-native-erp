"""fix_user_profile_role_user_fks

Revision ID: f9a3c5e7b2d4
Revises: e2b6f8a1d5c7
Create Date: 2026-07-10 10:30:00.000000

Summary
-------
Same class of bug as tenant_audit_logs (a3f9c2d1e8b7), the finance tables
(b4e0d3f2a9c6) and universal_item_master (c7d1e5f4b3a2): user_profiles.
created_by/updated_by and tenant_user_roles.created_by were constrained to
user_profiles.id, but app/api/v1/endpoints/users.py's provision_user() and
update_user() endpoints populate them from request.state.user_id (the
JWT-verified user_accounts.id), so every user provisioning call with an
authenticated actor - i.e. every real call - raised
ForeignKeyViolationError. Retarget to user_accounts.

tenant_user_roles.user_id is intentionally left pointing at
user_profiles.id - that column legitimately identifies which profile
holds the role, not who granted it.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f9a3c5e7b2d4'
down_revision = 'e2b6f8a1d5c7'
branch_labels = None
depends_on = None

_CHANGES = [
    ("user_profiles", "created_by", "user_profiles_created_by_fkey", "SET NULL"),
    ("user_profiles", "updated_by", "user_profiles_updated_by_fkey", "SET NULL"),
    ("tenant_user_roles", "created_by", "tenant_user_roles_created_by_fkey", "SET NULL"),
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
