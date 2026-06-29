from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.plans import FREE_PLAN, PLAN_CONFIGS, get_plan_config
from app.models.subscription_plan import SubscriptionPlan
from app.schemas.plan import (
    PublicSubscriptionPlanResponse,
    SubscriptionPlanCreateRequest,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdateRequest,
)


@dataclass(frozen=True)
class ResolvedPlan:
    key: str
    name: str
    price: int
    billing_cycle: str
    chat_limit: int | None
    translation_limit: int
    ai_provider: str
    button_text: str
    is_popular: bool
    is_active: bool
    sort_order: int
    image_upload_daily_limit: int
    image_generation_monthly_limit: int
    features_note: str


DEFAULT_PLAN_ROWS = [
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
    },
]


def _fallback_row(plan_key: str) -> dict:
    config = get_plan_config(plan_key)
    default_row = next((row for row in DEFAULT_PLAN_ROWS if row["plan_key"] == config.key), None)
    if default_row:
        return default_row
    return {
        "plan_key": config.key,
        "name": config.label,
        "price": config.price_inr,
        "billing_cycle": "free" if config.key == FREE_PLAN else "month",
        "chat_limit": config.chat_daily_limit,
        "translation_limit": config.translation_daily_limit,
        "ai_provider": config.features_note,
        "button_text": "Included by default" if config.key == FREE_PLAN else f"Pay for {config.label}",
        "is_popular": False,
        "is_active": True,
        "sort_order": 99,
    }


def _serialize_plan(plan: SubscriptionPlan) -> SubscriptionPlanResponse:
    return SubscriptionPlanResponse.model_validate(plan, from_attributes=True)


def _serialize_public_plan(plan: SubscriptionPlan) -> PublicSubscriptionPlanResponse:
    return PublicSubscriptionPlanResponse.model_validate(plan, from_attributes=True)


def _get_plan_or_404(db: Session, plan_id: int) -> SubscriptionPlan:
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


def list_admin_plans(db: Session) -> list[SubscriptionPlanResponse]:
    plans = db.query(SubscriptionPlan).order_by(SubscriptionPlan.sort_order.asc(), SubscriptionPlan.id.asc()).all()
    return [_serialize_plan(plan) for plan in plans]


def list_public_plans(db: Session) -> list[PublicSubscriptionPlanResponse]:
    plans = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.sort_order.asc(), SubscriptionPlan.id.asc())
        .all()
    )
    return [_serialize_public_plan(plan) for plan in plans]


def create_admin_plan(db: Session, payload: SubscriptionPlanCreateRequest) -> SubscriptionPlanResponse:
    existing = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_key == payload.plan_key.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plan key already exists")

    plan = SubscriptionPlan(
        plan_key=payload.plan_key.lower(),
        name=payload.name.strip(),
        price=payload.price,
        billing_cycle=payload.billing_cycle.strip(),
        chat_limit=payload.chat_limit,
        translation_limit=payload.translation_limit,
        ai_provider=payload.ai_provider.strip(),
        button_text=payload.button_text.strip(),
        is_popular=payload.is_popular,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


def update_admin_plan(db: Session, plan_id: int, payload: SubscriptionPlanUpdateRequest) -> SubscriptionPlanResponse:
    plan = _get_plan_or_404(db, plan_id)
    plan.name = payload.name.strip()
    plan.price = payload.price
    plan.billing_cycle = payload.billing_cycle.strip()
    plan.chat_limit = payload.chat_limit
    plan.translation_limit = payload.translation_limit
    plan.ai_provider = payload.ai_provider.strip()
    plan.button_text = payload.button_text.strip()
    plan.is_popular = payload.is_popular
    plan.is_active = payload.is_active
    plan.sort_order = payload.sort_order
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


def deactivate_admin_plan(db: Session, plan_id: int) -> SubscriptionPlanResponse:
    plan = _get_plan_or_404(db, plan_id)
    if plan.plan_key == FREE_PLAN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Free plan cannot be deleted")
    plan.is_active = False
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


def resolve_plan(db: Session, plan_key: str | None) -> ResolvedPlan:
    normalized_key = (plan_key or FREE_PLAN).lower()
    record = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_key == normalized_key).first()
    fallback = _fallback_row(normalized_key)
    config = PLAN_CONFIGS.get(normalized_key, PLAN_CONFIGS[FREE_PLAN])

    return ResolvedPlan(
        key=normalized_key,
        name=record.name if record else fallback["name"],
        price=record.price if record else fallback["price"],
        billing_cycle=record.billing_cycle if record else fallback["billing_cycle"],
        chat_limit=record.chat_limit if record else fallback["chat_limit"],
        translation_limit=record.translation_limit if record else fallback["translation_limit"],
        ai_provider=record.ai_provider if record else fallback["ai_provider"],
        button_text=record.button_text if record else fallback["button_text"],
        is_popular=record.is_popular if record else fallback["is_popular"],
        is_active=record.is_active if record else fallback["is_active"],
        sort_order=record.sort_order if record else fallback["sort_order"],
        image_upload_daily_limit=config.image_upload_daily_limit,
        image_generation_monthly_limit=config.image_generation_monthly_limit,
        features_note=record.ai_provider if record else fallback["ai_provider"],
    )
