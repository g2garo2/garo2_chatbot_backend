"""add subscription plans table

Revision ID: 20260630_000004
Revises: 20260629_000003
Create Date: 2026-06-30 00:00:04
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "20260630_000004"
down_revision = "20260629_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_key", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("billing_cycle", sa.String(length=30), nullable=False, server_default="month"),
        sa.Column("chat_limit", sa.Integer(), nullable=True),
        sa.Column("translation_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_provider", sa.Text(), nullable=False),
        sa.Column("button_text", sa.String(length=255), nullable=False),
        sa.Column("is_popular", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_key"),
    )
    op.create_index("ix_subscription_plans_plan_key", "subscription_plans", ["plan_key"])

    subscription_plans = sa.table(
        "subscription_plans",
        sa.column("plan_key", sa.String(length=50)),
        sa.column("name", sa.String(length=100)),
        sa.column("price", sa.Integer()),
        sa.column("billing_cycle", sa.String(length=30)),
        sa.column("chat_limit", sa.Integer()),
        sa.column("translation_limit", sa.Integer()),
        sa.column("ai_provider", sa.Text()),
        sa.column("button_text", sa.String(length=255)),
        sa.column("is_popular", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    now = datetime.now(timezone.utc)
    op.bulk_insert(
        subscription_plans,
        [
            {
                "plan_key": "free",
                "name": "Free",
                "price": 0,
                "billing_cycle": "free",
                "chat_limit": None,
                "translation_limit": 8,
                "ai_provider": "English chat uses OpenRouter free model. Garo chat requires a paid plan. Translation uses Gemini.",
                "button_text": "Included by default",
                "is_popular": False,
                "is_active": True,
                "sort_order": 1,
                "created_at": now,
                "updated_at": now,
            },
            {
                "plan_key": "plus",
                "name": "Plus",
                "price": 100,
                "billing_cycle": "month",
                "chat_limit": 20,
                "translation_limit": 20,
                "ai_provider": "All features use Gemini.",
                "button_text": "Pay for Plus",
                "is_popular": True,
                "is_active": True,
                "sort_order": 2,
                "created_at": now,
                "updated_at": now,
            },
            {
                "plan_key": "pro",
                "name": "Pro",
                "price": 299,
                "billing_cycle": "month",
                "chat_limit": 80,
                "translation_limit": 80,
                "ai_provider": "All features use Gemini.",
                "button_text": "Pay for Pro",
                "is_popular": False,
                "is_active": True,
                "sort_order": 3,
                "created_at": now,
                "updated_at": now,
            },
            {
                "plan_key": "ultra",
                "name": "Ultra",
                "price": 1099,
                "billing_cycle": "month",
                "chat_limit": 200,
                "translation_limit": 200,
                "ai_provider": "All features use Gemini.",
                "button_text": "Pay for Ultra",
                "is_popular": False,
                "is_active": True,
                "sort_order": 4,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_subscription_plans_plan_key", table_name="subscription_plans")
    op.drop_table("subscription_plans")
