"""phase4_rbac_updates

Revision ID: V002
Revises: u3d4e5f6a1b2
Create Date: 2026-07-07 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'V002'
down_revision: Union[str, None] = 'u3d4e5f6a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy.exc import ProgrammingError
    import asyncpg
    
    def safe_add_column(table, col):
        try:
            op.add_column(table, col)
        except Exception as e:
            if "already exists" in str(e) or "DuplicateColumnError" in str(e):
                pass
            else:
                raise
                
    def safe_drop_column(table, col):
        try:
            op.drop_column(table, col)
        except Exception as e:
            if "does not exist" in str(e):
                pass
            else:
                raise
                
    def safe_add_fk(fk_name, source, target, local, remote, **kwargs):
        try:
            op.create_foreign_key(fk_name, source, target, local, remote, **kwargs)
        except Exception as e:
            if "already exists" in str(e):
                pass
            else:
                raise

    # Update user_profiles
    safe_add_column('user_profiles', sa.Column('first_name', sa.String(length=128), nullable=True))
    safe_add_column('user_profiles', sa.Column('last_name', sa.String(length=128), nullable=True))
    safe_add_column('user_profiles', sa.Column('profile_image', sa.String(), nullable=True))
    safe_add_column('user_profiles', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))
    safe_add_column('user_profiles', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    safe_add_column('user_profiles', sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True))
    safe_add_column('user_profiles', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    
    safe_add_fk(None, 'user_profiles', 'user_profiles', ['created_by'], ['id'], ondelete='SET NULL')
    safe_add_fk(None, 'user_profiles', 'user_profiles', ['updated_by'], ['id'], ondelete='SET NULL')
    
    safe_drop_column('user_profiles', 'full_name')
    safe_drop_column('user_profiles', 'avatar_url')
    
    # Update tenant_roles
    safe_add_column('tenant_roles', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    safe_add_column('tenant_roles', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    safe_add_column('tenant_roles', sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True))
    safe_add_fk(None, 'tenant_roles', 'user_profiles', ['created_by'], ['id'], ondelete='SET NULL')
    safe_add_fk(None, 'tenant_roles', 'user_profiles', ['updated_by'], ['id'], ondelete='SET NULL')

    # Update tenant_permissions
    safe_add_column('tenant_permissions', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    safe_add_column('tenant_permissions', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    safe_add_column('tenant_permissions', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    safe_add_column('tenant_permissions', sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True))
    safe_add_fk(None, 'tenant_permissions', 'user_profiles', ['created_by'], ['id'], ondelete='SET NULL')
    safe_add_fk(None, 'tenant_permissions', 'user_profiles', ['updated_by'], ['id'], ondelete='SET NULL')

    # Update tenant_role_permissions
    safe_add_column('tenant_role_permissions', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    safe_add_fk(None, 'tenant_role_permissions', 'user_profiles', ['created_by'], ['id'], ondelete='SET NULL')
    
    # Update tenant_user_roles
    safe_add_column('tenant_user_roles', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    safe_add_fk(None, 'tenant_user_roles', 'user_profiles', ['created_by'], ['id'], ondelete='SET NULL')

def downgrade() -> None:
    pass
