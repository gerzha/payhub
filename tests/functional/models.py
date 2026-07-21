from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class OrderCreateRequest(BaseModel):
    product_id: str
    provider: Literal["stripe_like", "paypal_like"]
    amount: Decimal
    currency: str = "USD"


class OrderResponse(BaseModel):
    id: int
    product_id: str
    provider: str
    status: str
    provider_transaction_id: str | None
    amount: Decimal
    currency: str
    retry_count: int
    created_at: str
    updated_at: str


class StatusEventMessage(BaseModel):
    order_id: int
    status: str
    provider: str
