from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.feedback_request import FeedbackRequest
from app.schemas.feedback import FeedbackRequestCreate, FeedbackRequestResponse

router = APIRouter()


@router.post(
    "/feedback",
    response_model=FeedbackRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_feedback_request(
    payload: FeedbackRequestCreate,
    db: Session = Depends(get_db),
) -> FeedbackRequestResponse:
    feedback_request = FeedbackRequest(
        name=payload.name.strip(),
        email=str(payload.email).strip().lower(),
        feedback_type=payload.feedback_type.strip().lower(),
        message=payload.message.strip(),
    )
    db.add(feedback_request)
    db.commit()
    db.refresh(feedback_request)
    return feedback_request
