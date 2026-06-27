from fastapi import APIRouter, Header, HTTPException, Request, status

from app.db.session import SessionLocal
from app.services.billing_service import sync_subscription_from_webhook
from app.services.razorpay_service import verify_webhook_signature

router = APIRouter()


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
) -> dict[str, str]:
    payload = await request.body()
    if not x_razorpay_signature or not verify_webhook_signature(payload, x_razorpay_signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay webhook signature")

    data = await request.json()
    subscription_payload = (
        data.get("payload", {})
        .get("subscription", {})
        .get("entity")
    ) or (
        data.get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    db = SessionLocal()
    try:
        sync_subscription_from_webhook(db, subscription_payload)
    finally:
        db.close()

    return {"message": "Webhook processed"}
