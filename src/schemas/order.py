from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class OrderCreateRequest(BaseModel):
    product_id: str
    provider: Literal["stripe_like", "paypal_like"]
    amount: Decimal
    currency: str = "USD"


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: str
    provider: str
    status: str
    provider_transaction_id: str | None
    amount: Decimal
    currency: str
    retry_count: int
    created_at: datetime
    updated_at: datetime
