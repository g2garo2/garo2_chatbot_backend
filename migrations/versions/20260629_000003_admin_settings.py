"""add admin settings table

Revision ID: 20260629_000003
Revises: 20260627_000002
Create Date: 2026-06-29 00:00:03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260629_000003"
down_revision = "20260627_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
