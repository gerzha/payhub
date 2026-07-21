import hashlib
import hmac
import json

_CANONICAL_JSON_KWARGS: dict = {"sort_keys": True, "separators": (",", ":")}


def paypal_like_resource(
    order_id: int,
    state: str = "COMPLETED",
    value: str = "19.99",
    currency_code: str = "USD",
) -> dict:
    return {
        "order_id": order_id,
        "txn_id": f"PAY-{order_id}",
        "state": state,
        "value": value,
        "currency_code": currency_code,
    }


def sign_paypal_like(resource: dict, secret: str) -> str:
    unsigned = {"resource": resource}
    canonical = json.dumps(unsigned, **_CANONICAL_JSON_KWARGS).encode()
    return hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()


def paypal_like_webhook_payload(
    order_id: int,
    secret: str,
    state: str = "COMPLETED",
    value: str = "19.99",
    currency_code: str = "USD",
) -> dict:
    resource = paypal_like_resource(order_id, state, value, currency_code)
    signature = sign_paypal_like(resource, secret)
    return {"resource": resource, "signature": signature}
