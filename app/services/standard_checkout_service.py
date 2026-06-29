from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.plans import PAID_PLANS
from app.models.payment import Payment
from app.models.user import User
from app.schemas.billing import CreateOrderResponse, VerifyPaymentResponse
from app.services.plan_service import resolve_plan
from app.services.razorpay_service import create_order, fetch_payment, verify_payment_signature


def create_standard_order(
    db: Session,
    user: User,
    amount: int,
    currency: str,
    receipt: str,
    plan: str | None = None,
) -> CreateOrderResponse:
    normalized_currency = (currency or "INR").upper()
    normalized_receipt = (receipt or "").strip()
    if amount < 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be at least 100 paise")
    if not normalized_receipt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Receipt is required")
    if len(normalized_receipt) > 40:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Receipt must be 40 characters or fewer")

    normalized_plan = plan.lower() if plan else None
    if normalized_plan:
        if normalized_plan not in PAID_PLANS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported paid plan")
        expected_amount = resolve_plan(db, normalized_plan).price * 100
        if amount != expected_amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount does not match the selected plan")

    order = create_order(amount=amount, currency=normalized_currency, receipt=normalized_receipt)
    return CreateOrderResponse(order_id=order["id"], amount=order["amount"], currency=order["currency"])


def verify_standard_payment(
    db: Session,
    user: User,
    order_id: str,
    payment_id: str,
    signature: str,
    plan: str | None = None,
) -> VerifyPaymentResponse:
    if not order_id or not payment_id or not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing payment verification fields")

    if not verify_payment_signature(order_id=order_id, payment_id=payment_id, signature=signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment signature mismatch")

    normalized_plan = plan.lower() if plan else None
    payment_details = fetch_payment(payment_id)
    if payment_details.get("order_id") != order_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment does not belong to the provided order")

    payment_status = (payment_details.get("status") or "").lower()
    if payment_status not in {"authorized", "captured"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment is not in a successful state")

    if db.query(Payment).filter(Payment.razorpay_payment_id == payment_id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This payment has already been processed")

    if normalized_plan in PAID_PLANS:
        expected_amount = resolve_plan(db, normalized_plan).price * 100
        if int(payment_details.get("amount") or 0) != expected_amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paid amount does not match the selected plan")
        user.plan = normalized_plan
        user.subscription_status = "manual_active"
        user.subscription_start = datetime.now(timezone.utc)
        user.subscription_end = user.subscription_start + timedelta(days=30)
        user.razorpay_subscription_id = None

    payment = Payment(
        user_id=user.id,
        plan=normalized_plan or user.plan,
        amount_inr=resolve_plan(db, normalized_plan or user.plan).price,
        provider="razorpay",
        status="paid",
        razorpay_payment_id=payment_id,
        razorpay_customer_id=user.razorpay_customer_id,
    )
    db.add(payment)
    db.add(user)
    db.commit()
    db.refresh(user)

    return VerifyPaymentResponse(
        success=True,
        message="Payment verified successfully",
        plan=normalized_plan or user.plan,
    )
