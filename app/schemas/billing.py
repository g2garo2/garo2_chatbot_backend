from pydantic import BaseModel


class CreateSubscriptionRequest(BaseModel):
    plan: str


class CreateOrderRequest(BaseModel):
    amount: int
    currency: str = "INR"
    receipt: str
    plan: str | None = None


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str


class CreateSubscriptionResponse(BaseModel):
    plan: str
    plan_label: str
    razorpay_key_id: str
    razorpay_subscription_id: str
    razorpay_customer_id: str | None
    amount_inr: int
    status: str


class VerifySubscriptionRequest(BaseModel):
    plan: str
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    plan: str | None = None


class VerifyPaymentResponse(BaseModel):
    success: bool
    message: str
    plan: str | None = None


class VerifySubscriptionResponse(BaseModel):
    message: str
    plan: str
    subscription_status: str
