from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.billing import (
    CreateSubscriptionRequest,
    CreateSubscriptionResponse,
    VerifySubscriptionRequest,
    VerifySubscriptionResponse,
)
from app.services.billing_service import create_user_subscription, verify_user_subscription

router = APIRouter()


@router.post("/create-subscription", response_model=CreateSubscriptionResponse)
def create_subscription_endpoint(
    payload: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreateSubscriptionResponse:
    return create_user_subscription(db, current_user, payload.plan.lower())


@router.post("/verify-subscription", response_model=VerifySubscriptionResponse)
def verify_subscription_endpoint(
    payload: VerifySubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerifySubscriptionResponse:
    return verify_user_subscription(
        db=db,
        user=current_user,
        plan=payload.plan.lower(),
        payment_id=payload.razorpay_payment_id,
        subscription_id=payload.razorpay_subscription_id,
        signature=payload.razorpay_signature,
    )
