"""add subscription and usage tables

Revision ID: 20260627_000002
Revises: 20260624_000001
Create Date: 2026-06-27 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260627_000002"
down_revision = "20260624_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("plan", sa.String(length=50), nullable=False, server_default="free"))
    op.add_column("users", sa.Column("subscription_status", sa.String(length=50), nullable=False, server_default="free"))
    op.add_column("users", sa.Column("razorpay_subscription_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("razorpay_customer_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("subscription_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("subscription_end", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "usage_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("chat_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("translation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_upload_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_usage_daily_user_date"),
    )
    op.create_index("ix_usage_daily_user_id", "usage_daily", ["user_id"])
    op.create_index("ix_usage_daily_usage_date", "usage_daily", ["usage_date"])

    op.create_table(
        "usage_monthly",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("usage_month", sa.String(length=7), nullable=False),
        sa.Column("image_generation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "usage_month", name="uq_usage_monthly_user_month"),
    )
    op.create_index("ix_usage_monthly_user_id", "usage_monthly", ["user_id"])
    op.create_index("ix_usage_monthly_usage_month", "usage_monthly", ["usage_month"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("amount_inr", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="razorpay"),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("razorpay_payment_id", sa.String(length=255), nullable=True),
        sa.Column("razorpay_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("razorpay_customer_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_payments_razorpay_payment_id", "payments", ["razorpay_payment_id"])
    op.create_index("ix_payments_razorpay_subscription_id", "payments", ["razorpay_subscription_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_razorpay_subscription_id", table_name="payments")
    op.drop_index("ix_payments_razorpay_payment_id", table_name="payments")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_usage_monthly_usage_month", table_name="usage_monthly")
    op.drop_index("ix_usage_monthly_user_id", table_name="usage_monthly")
    op.drop_table("usage_monthly")

    op.drop_index("ix_usage_daily_usage_date", table_name="usage_daily")
    op.drop_index("ix_usage_daily_user_id", table_name="usage_daily")
    op.drop_table("usage_daily")

    op.drop_column("users", "subscription_end")
    op.drop_column("users", "subscription_start")
    op.drop_column("users", "razorpay_customer_id")
    op.drop_column("users", "razorpay_subscription_id")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "plan")
