"""add feedback requests table

Revision ID: 20260630_000006
Revises: 20260630_000005
Create Date: 2026-06-30 00:00:06
"""

from alembic import op
import sqlalchemy as sa


revision = "20260630_000006"
down_revision = "20260630_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("feedback_type", sa.String(length=50), nullable=False, server_default="general"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_requests_email", "feedback_requests", ["email"])


def downgrade() -> None:
    op.drop_index("ix_feedback_requests_email", table_name="feedback_requests")
    op.drop_table("feedback_requests")
