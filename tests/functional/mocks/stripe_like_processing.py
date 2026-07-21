import hashlib
import hmac


def stripe_like_webhook_payload(
    order_id: int,
    status: str = "payment_succeeded",
    amount: str = "19.99",
    currency: str = "USD",
) -> dict:
    return {
        "order_id": order_id,
        "transaction_id": f"tx_{order_id}",
        "event": status,
        "amount": amount,
        "currency": currency,
    }


def sign_stripe_like(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
