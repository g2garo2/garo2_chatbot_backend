from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.account_deletion_request import AccountDeletionRequest
from app.schemas.account_deletion import AccountDeletionRequestCreate, AccountDeletionRequestResponse

router = APIRouter()


@router.post(
    "/account-deletion-request",
    response_model=AccountDeletionRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account_deletion_request(
    payload: AccountDeletionRequestCreate,
    db: Session = Depends(get_db),
) -> AccountDeletionRequestResponse:
    deletion_request = AccountDeletionRequest(
        name=payload.name.strip(),
        email=str(payload.email).strip().lower(),
        reason=payload.reason.strip(),
    )
    db.add(deletion_request)
    db.commit()
    db.refresh(deletion_request)
    return deletion_request
