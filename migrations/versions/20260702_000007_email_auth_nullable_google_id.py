"""allow users without google id

Revision ID: 20260702_000007
Revises: 20260630_000006
Create Date: 2026-07-02 00:00:07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260702_000007"
down_revision = "20260630_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "google_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "google_id",
        existing_type=sa.String(length=255),
        nullable=False,
    )
