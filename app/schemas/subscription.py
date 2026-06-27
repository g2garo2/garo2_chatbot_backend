from datetime import datetime

from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    plan: str
    plan_label: str
    subscription_status: str
    price_inr: int
    razorpay_subscription_id: str | None
    razorpay_customer_id: str | None
    subscription_start: datetime | None
    subscription_end: datetime | None
    features_note: str
