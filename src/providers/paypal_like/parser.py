import json

from src.schemas.webhook import NormalizedWebhook

_STATE_TO_STATUS = {
    "COMPLETED": "paid",
    "DENIED": "failed",
}


class PaypalLikeParser:
    def parse(self, raw_body: bytes) -> NormalizedWebhook:
        payload = json.loads(raw_body)
        resource = payload["resource"]
        return NormalizedWebhook(
            order_id=resource["order_id"],
            provider_transaction_id=resource["txn_id"],
            status=_STATE_TO_STATUS[resource["state"]],
            amount=resource["value"],
            currency=resource["currency_code"],
        )
