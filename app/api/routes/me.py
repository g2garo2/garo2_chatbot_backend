from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse
from app.schemas.usage import UsageResponse
from app.services.billing_service import build_subscription_response
from app.services.usage_service import build_usage_response

router = APIRouter()


@router.get("/usage", response_model=UsageResponse)
def get_usage(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UsageResponse:
    return build_usage_response(db, current_user)


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(current_user: User = Depends(get_current_user)) -> SubscriptionResponse:
    return build_subscription_response(current_user)
