import json

from src.schemas.webhook import NormalizedWebhook

_EVENT_TO_STATUS = {
    "payment_succeeded": "paid",
    "payment_failed": "failed",
}


class StripeLikeParser:
    def parse(self, raw_body: bytes) -> NormalizedWebhook:
        payload = json.loads(raw_body)
        return NormalizedWebhook(
            order_id=payload["order_id"],
            provider_transaction_id=payload["transaction_id"],
            status=_EVENT_TO_STATUS[payload["event"]],
            amount=payload["amount"],
            currency=payload["currency"],
        )
