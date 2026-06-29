from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.plans import (
    ACTIVE_SUBSCRIPTION_STATUSES,
    FREE_PLAN,
    PAID_PLANS,
    SUBSCRIPTION_DOWNGRADE_STATUSES,
)
from app.models.payment import Payment
from app.models.user import User
from app.schemas.billing import CreateSubscriptionResponse, VerifySubscriptionResponse
from app.schemas.subscription import SubscriptionResponse
from app.services.plan_service import resolve_plan
from app.services.razorpay_service import create_customer, create_subscription, fetch_subscription, verify_subscription_signature


def _plan_id_for(plan: str) -> str:
    mapping = {
        "plus": settings.razorpay_plan_plus,
        "pro": settings.razorpay_plan_pro,
        "ultra": settings.razorpay_plan_ultra,
    }
    plan_id = mapping.get(plan)
    if not plan_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported paid plan")
    return plan_id


def _find_plan_from_razorpay_plan_id(razorpay_plan_id: str) -> str:
    mapping = {
        settings.razorpay_plan_plus: "plus",
        settings.razorpay_plan_pro: "pro",
        settings.razorpay_plan_ultra: "ultra",
    }
    plan = mapping.get(razorpay_plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown Razorpay plan mapping")
    return plan


def build_subscription_response(db: Session, user: User) -> SubscriptionResponse:
    plan = resolve_plan(db, user.plan)
    return SubscriptionResponse(
        plan=plan.key,
        plan_label=plan.name,
        subscription_status=user.subscription_status,
        price_inr=plan.price,
        razorpay_subscription_id=user.razorpay_subscription_id,
        razorpay_customer_id=user.razorpay_customer_id,
        subscription_start=user.subscription_start,
        subscription_end=user.subscription_end,
        features_note=plan.features_note,
    )


def create_user_subscription(db: Session, user: User, plan_key: str) -> CreateSubscriptionResponse:
    if plan_key not in PAID_PLANS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only paid plans can create Razorpay subscriptions")

    plan = resolve_plan(db, plan_key)
    if not user.razorpay_customer_id:
        customer = create_customer(user.name, user.email)
        user.razorpay_customer_id = customer.get("id")

    subscription = create_subscription(plan_id=_plan_id_for(plan_key), total_count=12)
    user.razorpay_subscription_id = subscription.get("id")
    user.subscription_status = subscription.get("status", "created")
    db.add(user)
    db.commit()
    db.refresh(user)

    return CreateSubscriptionResponse(
        plan=plan.key,
        plan_label=plan.name,
        razorpay_key_id=settings.razorpay_key_id,
        razorpay_subscription_id=subscription["id"],
        razorpay_customer_id=user.razorpay_customer_id,
        amount_inr=plan.price,
        status=subscription.get("status", "created"),
    )


def _apply_subscription_to_user(user: User, subscription: dict) -> None:
    plan_key = _find_plan_from_razorpay_plan_id(subscription.get("plan_id", ""))
    user.plan = plan_key
    user.subscription_status = subscription.get("status", "active")
    user.razorpay_subscription_id = subscription.get("id")
    user.subscription_start = datetime.now(timezone.utc)

    timestamp = subscription.get("end_at") or subscription.get("charge_at")
    if timestamp:
        user.subscription_end = datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _downgrade_user(user: User) -> None:
    user.plan = FREE_PLAN
    user.subscription_status = "free"
    user.subscription_start = None
    user.subscription_end = None


def verify_user_subscription(
    db: Session,
    user: User,
    plan: str,
    payment_id: str,
    subscription_id: str,
    signature: str,
) -> VerifySubscriptionResponse:
    if plan not in PAID_PLANS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan for subscription verification")

    if not verify_subscription_signature(payment_id, subscription_id, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay signature")

    subscription = fetch_subscription(subscription_id)
    _apply_subscription_to_user(user, subscription)
    payment = Payment(
        user_id=user.id,
        plan=plan,
        amount_inr=resolve_plan(db, plan).price,
        provider="razorpay",
        status=subscription.get("status", "active"),
        razorpay_payment_id=payment_id,
        razorpay_subscription_id=subscription_id,
        razorpay_customer_id=user.razorpay_customer_id,
    )
    db.add(payment)
    db.add(user)
    db.commit()
    db.refresh(user)

    return VerifySubscriptionResponse(
        message="Subscription verified successfully",
        plan=user.plan,
        subscription_status=user.subscription_status,
    )


def sync_subscription_from_webhook(db: Session, subscription_payload: dict) -> None:
    subscription_id = subscription_payload.get("id") or subscription_payload.get("subscription_id")
    if not subscription_id:
        return

    user = db.query(User).filter(User.razorpay_subscription_id == subscription_id).first()
    if not user:
        return

    if not subscription_payload.get("plan_id") or not subscription_payload.get("status"):
        subscription_payload = fetch_subscription(subscription_id)

    status_value = (subscription_payload.get("status") or "").lower()
    if status_value in SUBSCRIPTION_DOWNGRADE_STATUSES:
        _downgrade_user(user)
    elif status_value in ACTIVE_SUBSCRIPTION_STATUSES:
        _apply_subscription_to_user(user, subscription_payload)
    elif status_value:
        user.subscription_status = status_value

    payment = Payment(
        user_id=user.id,
        plan=user.plan,
        amount_inr=resolve_plan(db, user.plan).price,
        provider="razorpay",
        status=status_value or "updated",
        razorpay_subscription_id=subscription_id,
        razorpay_customer_id=user.razorpay_customer_id,
    )
    db.add(payment)
    db.add(user)
    db.commit()
