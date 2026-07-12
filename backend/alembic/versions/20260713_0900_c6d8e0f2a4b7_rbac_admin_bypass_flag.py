"""rbac_admin_bypass_flag

Revision ID: c6d8e0f2a4b7
Revises: b5c7d9e2f4a6
Create Date: 2026-07-13 09:00:00.000000

Summary
-------
RequirePermission's admin bypass (middleware/rbac.py) keyed off role name
string ("Super Admin", "Organization Admin") rather than an immutable flag.
Two problems: renaming either role silently breaks admin access, and any
tenant admin who can create custom roles (a real capability — see
RBAC:Roles:Create in app/api/v1/endpoints/rbac.py) could create a role
named exactly "Super Admin" for themselves and self-escalate, since the
bypass check only ever looked at the string.

Adds tenant_roles.is_admin_bypass (boolean, default false) and backfills it
True for exactly the two roles the old name-string check already granted
bypass to, so this is a behavior-preserving migration — no admin's access
changes. Going forward, middleware/rbac.py checks this flag instead of the
name, and seed_admin.py sets it explicitly when provisioning a new
tenant's Super Admin role.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c6d8e0f2a4b7'
down_revision = 'b5c7d9e2f4a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'tenant_roles',
        sa.Column('is_admin_bypass', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.execute(
        "UPDATE tenant_roles SET is_admin_bypass = true "
        "WHERE name IN ('Super Admin', 'Organization Admin')"
    )


def downgrade() -> None:
    op.drop_column('tenant_roles', 'is_admin_bypass')
