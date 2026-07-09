"""add_warehouse_manager_id

Revision ID: d8f2a6c9e1b4
Revises: c7d1e5f4b3a2
Create Date: 2026-07-10 09:15:00.000000

Summary
-------
UniversalWarehouseBase/Create/Update schemas have always defined a
manager_id field, but universal_warehouses never had a matching column -
create_warehouse() does `UniversalWarehouse(**payload.model_dump())`,
so every warehouse-create/update request raised
`TypeError: 'manager_id' is an invalid keyword argument`. Adds the
missing column, FK'd to user_accounts (the JWT-verified identity, see
a3f9c2d1e8b7/b4e0d3f2a9c6/c7d1e5f4b3a2 for the established precedent).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd8f2a6c9e1b4'
down_revision = 'c7d1e5f4b3a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'universal_warehouses',
        sa.Column('manager_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='public',
    )
    op.create_foreign_key(
        'universal_warehouses_manager_id_fkey', 'universal_warehouses', 'user_accounts',
        ['manager_id'], ['id'], source_schema='public', referent_schema='public', ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('universal_warehouses_manager_id_fkey', 'universal_warehouses', schema='public', type_='foreignkey')
    op.drop_column('universal_warehouses', 'manager_id', schema='public')
