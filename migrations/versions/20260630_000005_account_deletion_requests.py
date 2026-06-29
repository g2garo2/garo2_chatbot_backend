"""add account deletion requests table

Revision ID: 20260630_000005
Revises: 20260630_000004
Create Date: 2026-06-30 00:00:05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260630_000005"
down_revision = "20260630_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_deletion_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_account_deletion_requests_email", "account_deletion_requests", ["email"])


def downgrade() -> None:
    op.drop_index("ix_account_deletion_requests_email", table_name="account_deletion_requests")
    op.drop_table("account_deletion_requests")
