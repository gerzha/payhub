from enum import StrEnum


class Provider(StrEnum):
    STRIPE_LIKE = "stripe_like"
    PAYPAL_LIKE = "paypal_like"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"
    HOLD = "HOLD"


class Routes(StrEnum):
    ORDERS = "orders"
    WEBHOOKS = "webhooks"


class StripeLikeEvent(StrEnum):
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"


class PaypalLikeState(StrEnum):
    COMPLETED = "COMPLETED"
    DENIED = "DENIED"


class Headers(StrEnum):
    SIGNATURE = "X-Signature"


INVALID_SIGNATURE = "garbage-signature"
