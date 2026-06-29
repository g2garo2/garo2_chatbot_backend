from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.plan import PublicSubscriptionPlanResponse
from app.services.plan_service import list_public_plans

router = APIRouter()


@router.get("/plans", response_model=list[PublicSubscriptionPlanResponse])
def get_public_plans(db: Session = Depends(get_db)) -> list[PublicSubscriptionPlanResponse]:
    return list_public_plans(db)
