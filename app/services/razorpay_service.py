import hashlib
import hmac

from fastapi import HTTPException, status
import razorpay

from app.core.config import settings

def _client() -> razorpay.Client:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Razorpay keys are not configured")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def _handle_sdk_error(exc: Exception) -> HTTPException:
    message = str(exc) or "Razorpay request failed"
    status_code = status.HTTP_502_BAD_GATEWAY
    if "Authentication" in message or "auth" in message.lower():
        status_code = status.HTTP_401_UNAUTHORIZED
    return HTTPException(status_code=status_code, detail=message)


def create_customer(name: str, email: str) -> dict:
    try:
        return _client().customer.create({"name": name, "email": email, "fail_existing": 0})
    except Exception as exc:
        raise _handle_sdk_error(exc) from exc


def create_order(amount: int, currency: str, receipt: str) -> dict:
    try:
        return _client().order.create({"amount": amount, "currency": currency, "receipt": receipt})
    except Exception as exc:
        raise _handle_sdk_error(exc) from exc


def fetch_payment(payment_id: str) -> dict:
    try:
        return _client().payment.fetch(payment_id)
    except Exception as exc:
        raise _handle_sdk_error(exc) from exc


def create_subscription(plan_id: str, total_count: int, customer_notify: int = 1) -> dict:
    try:
        return _client().subscription.create(
            {
                "plan_id": plan_id,
                "total_count": total_count,
                "customer_notify": customer_notify,
            }
        )
    except Exception as exc:
        raise _handle_sdk_error(exc) from exc


def fetch_subscription(subscription_id: str) -> dict:
    try:
        return _client().subscription.fetch(subscription_id)
    except Exception as exc:
        raise _handle_sdk_error(exc) from exc


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    expected = hmac.new(
        settings.razorpay_key_secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_subscription_signature(payment_id: str, subscription_id: str, signature: str) -> bool:
    expected = hmac.new(
        settings.razorpay_key_secret.encode("utf-8"),
        f"{payment_id}|{subscription_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(settings.razorpay_webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
