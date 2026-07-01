"""add password hash for email auth

Revision ID: 20260702_000008
Revises: 20260702_000007
Create Date: 2026-07-02 00:00:08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260702_000008"
down_revision = "20260702_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
