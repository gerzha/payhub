from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class NormalizedWebhook(BaseModel):
    order_id: int
    provider_transaction_id: str
    status: Literal["paid", "failed"]
    amount: Decimal
    currency: str
