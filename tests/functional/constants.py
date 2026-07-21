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
