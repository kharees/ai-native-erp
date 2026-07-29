"""dedupe_and_constrain_tenant_permissions

Revision ID: e2f4a6b8c0d2
Revises: 148966fd2a99
Create Date: 2026-07-28 10:15:00.000000

Root cause: TenantPermission's original migration
(20260704_1550_d4e5f6a1b2c3_rbac.py) already declares a unique
constraint on (module, feature, action) -- uix_permission_def -- but the
SQLAlchemy model (app/models/rbac.py) never mirrored it via
__table_args__. Any database bootstrapped via Base.metadata.create_all()
(which reads the model, not this migration file) therefore got a
constraint-less table. Several non-idempotent get-or-create call sites
across the test suite then each inserted their own copy of the same
tuple over repeated runs -- one local dev DB had accumulated over 1200
rows for what should have been ~15 unique permission tuples (one tuple
alone had 381 duplicates), causing MultipleResultsFound crashes in every
caller using .scalar_one_or_none() without a .limit(1) guard.

This migration is idempotent and safe to run against ANY database
regardless of its starting state:
  - A fresh database that got uix_permission_def from the original rbac
    migration: the dedupe loop below is a no-op (no duplicate groups to
    find), and the constraint-add is skipped (already present).
  - A database like the one this bug was found on, bootstrapped via
    create_all() with no constraint and real accumulated duplicates: the
    dedupe loop merges each duplicate group down to one canonical row
    (oldest created_at) before the constraint is added -- Postgres
    refuses to add a unique constraint over data that would violate it.

Merge, not blind delete
--------------------------
Deleting duplicate tenant_permissions rows outright would CASCADE-delete
any tenant_role_permissions row pointing at that specific duplicate (see
that table's ondelete='CASCADE' FK), silently revoking whichever tenant
roles happened to reference it. Instead, every tenant_role_permissions
row pointing at a duplicate is repointed to the canonical row first --
dropped instead only if that exact (role_id, canonical_id) link already
exists (repointing would otherwise violate tenant_role_permissions' own
uix_role_permission unique constraint) -- and only then are the now-
unreferenced duplicate tenant_permissions rows deleted.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e2f4a6b8c0d2'
down_revision: Union[str, None] = '148966fd2a99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    metadata = sa.MetaData()
    tenant_permissions = sa.Table('tenant_permissions', metadata, autoload_with=conn)
    tenant_role_permissions = sa.Table('tenant_role_permissions', metadata, autoload_with=conn)

    dup_groups = conn.execute(
        sa.select(tenant_permissions.c.module, tenant_permissions.c.feature, tenant_permissions.c.action)
        .group_by(tenant_permissions.c.module, tenant_permissions.c.feature, tenant_permissions.c.action)
        .having(sa.func.count() > 1)
    ).all()

    for module, feature, action in dup_groups:
        rows = conn.execute(
            sa.select(tenant_permissions.c.id)
            .where(
                tenant_permissions.c.module == module,
                tenant_permissions.c.feature == feature,
                tenant_permissions.c.action == action,
            )
            .order_by(tenant_permissions.c.created_at.asc(), tenant_permissions.c.id.asc())
        ).all()
        canonical_id = rows[0].id
        duplicate_ids = [r.id for r in rows[1:]]

        canonical_role_ids = {
            r.role_id for r in conn.execute(
                sa.select(tenant_role_permissions.c.role_id)
                .where(tenant_role_permissions.c.permission_id == canonical_id)
            ).all()
        }

        for dup_id in duplicate_ids:
            dup_links = conn.execute(
                sa.select(tenant_role_permissions.c.id, tenant_role_permissions.c.role_id)
                .where(tenant_role_permissions.c.permission_id == dup_id)
            ).all()
            for link in dup_links:
                if link.role_id in canonical_role_ids:
                    # This role already has a real grant via the
                    # canonical row -- the duplicate-pointing link is
                    # pure redundancy, drop it outright.
                    conn.execute(
                        sa.delete(tenant_role_permissions).where(tenant_role_permissions.c.id == link.id)
                    )
                else:
                    conn.execute(
                        sa.update(tenant_role_permissions)
                        .where(tenant_role_permissions.c.id == link.id)
                        .values(permission_id=canonical_id)
                    )
                    canonical_role_ids.add(link.role_id)

            conn.execute(sa.delete(tenant_permissions).where(tenant_permissions.c.id == dup_id))

    already_constrained = conn.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = 'uix_permission_def' "
        "AND conrelid = 'public.tenant_permissions'::regclass"
    )).first()
    if already_constrained is None:
        op.create_unique_constraint('uix_permission_def', 'tenant_permissions', ['module', 'feature', 'action'])


def downgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = 'uix_permission_def' "
        "AND conrelid = 'public.tenant_permissions'::regclass"
    )).first()
    if exists is not None:
        op.drop_constraint('uix_permission_def', 'tenant_permissions', type_='unique')
    # Merged/deleted duplicate rows are not restored -- this downgrade
    # only reverses the schema change (the constraint), matching this
    # repo's other migrations' convention of not attempting to undo data
    # cleanups on downgrade.
