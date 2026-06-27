from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.plans import FREE_PLAN, get_plan_config
from app.models.message import Message
from app.models.usage_daily import UsageDaily
from app.models.usage_monthly import UsageMonthly
from app.models.user import User
from app.schemas.usage import UsageLimitView, UsageResponse

UPGRADE_LIMIT_MESSAGE = "You have reached your limit for this plan. Upgrade your plan to continue."


@dataclass
class UsageSnapshot:
    daily: UsageDaily
    monthly: UsageMonthly


def get_or_create_daily_usage(db: Session, user_id: int, usage_date: date) -> UsageDaily:
    usage = db.query(UsageDaily).filter(UsageDaily.user_id == user_id, UsageDaily.usage_date == usage_date).first()
    if usage:
        return usage
    usage = UsageDaily(user_id=user_id, usage_date=usage_date)
    db.add(usage)
    db.flush()
    return usage


def get_or_create_monthly_usage(db: Session, user_id: int, usage_month: str) -> UsageMonthly:
    usage = db.query(UsageMonthly).filter(UsageMonthly.user_id == user_id, UsageMonthly.usage_month == usage_month).first()
    if usage:
        return usage
    usage = UsageMonthly(user_id=user_id, usage_month=usage_month)
    db.add(usage)
    db.flush()
    return usage


def get_usage_snapshot(db: Session, user: User) -> UsageSnapshot:
    today = datetime.now(timezone.utc).date()
    month_key = today.strftime("%Y-%m")
    return UsageSnapshot(
        daily=get_or_create_daily_usage(db, user.id, today),
        monthly=get_or_create_monthly_usage(db, user.id, month_key),
    )


def _remaining(limit: int | None, used: int) -> int | None:
    if limit is None:
        return None
    return max(limit - used, 0)


def _raise_limit(feature: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"{UPGRADE_LIMIT_MESSAGE} [{feature}]",
    )


def enforce_chat_limit(db: Session, user: User) -> None:
    plan = get_plan_config(user.plan)
    snapshot = get_usage_snapshot(db, user)
    if plan.chat_daily_limit is not None and snapshot.daily.chat_count >= plan.chat_daily_limit:
        _raise_limit("chat")

    if plan.key == FREE_PLAN:
        latest_user_message = (
            db.query(Message)
            .join(Message.chat)
            .filter(Message.role == "user", Message.chat.has(user_id=user.id))
            .order_by(Message.created_at.desc())
            .first()
        )
        if latest_user_message and latest_user_message.created_at:
            now = datetime.now(timezone.utc)
            latest_at = latest_user_message.created_at
            if latest_at.tzinfo is None:
                latest_at = latest_at.replace(tzinfo=timezone.utc)
            if (now - latest_at).total_seconds() < 2:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Please wait a moment before sending another free-plan chat request.",
                )


def enforce_translation_limit(db: Session, user: User) -> None:
    plan = get_plan_config(user.plan)
    snapshot = get_usage_snapshot(db, user)
    if snapshot.daily.translation_count >= plan.translation_daily_limit:
        _raise_limit("translation")


def enforce_image_upload_limit(db: Session, user: User) -> None:
    plan = get_plan_config(user.plan)
    snapshot = get_usage_snapshot(db, user)
    if snapshot.daily.image_upload_count >= plan.image_upload_daily_limit:
        _raise_limit("image_upload")


def enforce_image_generation_limit(db: Session, user: User) -> None:
    plan = get_plan_config(user.plan)
    snapshot = get_usage_snapshot(db, user)
    if snapshot.monthly.image_generation_count >= plan.image_generation_monthly_limit:
        _raise_limit("image_generation")


def increment_chat_usage(db: Session, user: User) -> None:
    snapshot = get_usage_snapshot(db, user)
    snapshot.daily.chat_count += 1
    db.add(snapshot.daily)


def increment_translation_usage(db: Session, user: User) -> None:
    snapshot = get_usage_snapshot(db, user)
    snapshot.daily.translation_count += 1
    db.add(snapshot.daily)


def increment_image_upload_usage(db: Session, user: User) -> None:
    snapshot = get_usage_snapshot(db, user)
    snapshot.daily.image_upload_count += 1
    db.add(snapshot.daily)


def increment_image_generation_usage(db: Session, user: User) -> None:
    snapshot = get_usage_snapshot(db, user)
    snapshot.monthly.image_generation_count += 1
    db.add(snapshot.monthly)


def build_usage_response(db: Session, user: User) -> UsageResponse:
    plan = get_plan_config(user.plan)
    snapshot = get_usage_snapshot(db, user)
    return UsageResponse(
        plan=plan.key,
        chat=UsageLimitView(
            used=snapshot.daily.chat_count,
            limit=plan.chat_daily_limit,
            remaining=_remaining(plan.chat_daily_limit, snapshot.daily.chat_count),
        ),
        translation=UsageLimitView(
            used=snapshot.daily.translation_count,
            limit=plan.translation_daily_limit,
            remaining=_remaining(plan.translation_daily_limit, snapshot.daily.translation_count),
        ),
        image_upload=UsageLimitView(
            used=snapshot.daily.image_upload_count,
            limit=plan.image_upload_daily_limit,
            remaining=_remaining(plan.image_upload_daily_limit, snapshot.daily.image_upload_count),
        ),
        image_generation=UsageLimitView(
            used=snapshot.monthly.image_generation_count,
            limit=plan.image_generation_monthly_limit,
            remaining=_remaining(plan.image_generation_monthly_limit, snapshot.monthly.image_generation_count),
        ),
    )
