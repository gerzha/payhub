import hashlib
import hmac
import json

STRIPE_LIKE_SECRET = "test_stripe_like_secret"
PAYPAL_LIKE_SECRET = "test_paypal_like_secret"


def sign_stripe_like(raw_body: bytes, secret: str = STRIPE_LIKE_SECRET) -> str:
    return hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()


def build_paypal_like_body(resource: dict, secret: str = PAYPAL_LIKE_SECRET) -> bytes:
    unsigned = {"resource": resource}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()
    return json.dumps({**unsigned, "signature": signature}).encode()
