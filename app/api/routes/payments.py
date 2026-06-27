from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.billing import CreateOrderRequest, CreateOrderResponse, VerifyPaymentRequest, VerifyPaymentResponse
from app.services.standard_checkout_service import create_standard_order, verify_standard_payment

router = APIRouter()


@router.post("/create-order", response_model=CreateOrderResponse)
def create_order_endpoint(
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreateOrderResponse:
    return create_standard_order(
        db=db,
        user=current_user,
        amount=payload.amount,
        currency=payload.currency,
        receipt=payload.receipt,
        plan=payload.plan,
    )


@router.post("/verify-payment", response_model=VerifyPaymentResponse)
def verify_payment_endpoint(
    payload: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerifyPaymentResponse:
    return verify_standard_payment(
        db=db,
        user=current_user,
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
        plan=payload.plan,
    )
