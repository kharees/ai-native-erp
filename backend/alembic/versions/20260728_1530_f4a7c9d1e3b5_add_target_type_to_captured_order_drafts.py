"""add_target_type_to_captured_order_drafts

Revision ID: f4a7c9d1e3b5
Revises: e2f4a6b8c0d2
Create Date: 2026-07-28 15:30:00.000000

Adds the photo-to-quotation flow alongside the existing photo-to-invoice
flow (see app/services/order_capture.py's confirm_draft): target_type
records which document confirm_draft() actually produced ("invoice",
the original/default behavior, or "quotation"), and
resulting_quotation_id mirrors the existing resulting_invoice_id column
for the new quotation path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f4a7c9d1e3b5'
down_revision: Union[str, None] = 'e2f4a6b8c0d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "captured_order_drafts",
        sa.Column("target_type", sa.String(16), nullable=False, server_default=sa.text("'invoice'")),
    )
    op.add_column(
        "captured_order_drafts",
        sa.Column("resulting_quotation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "captured_order_drafts_resulting_quotation_id_fkey",
        "captured_order_drafts", "universal_sales_quotations",
        ["resulting_quotation_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "captured_order_drafts_resulting_quotation_id_fkey", "captured_order_drafts", type_="foreignkey",
    )
    op.drop_column("captured_order_drafts", "resulting_quotation_id")
    op.drop_column("captured_order_drafts", "target_type")
