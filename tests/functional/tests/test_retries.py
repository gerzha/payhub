import json

import pytest

from clients import PayhubClient
from constants import Headers, Provider, StripeLikeEvent
from mocks.stripe_like_processing import sign_stripe_like, stripe_like_webhook_payload
from qa_toolkit.randomize import generate_random_int_unique
from qa_toolkit.waiter import smart_wait
from settings import STRIPE_LIKE_SECRET


def test_webhook_for_unknown_provider_returns_404(payhub_client: PayhubClient) -> None:
    response = payhub_client.send_webhook("unknown_provider_like", {"foo": "bar"})

    assert response.status_code == 404


def test_webhook_for_nonexistent_order_is_dropped_without_error(payhub_client, sqs_client) -> None:
    nonexistent_order_id = generate_random_int_unique()
    payload = stripe_like_webhook_payload(
        order_id=nonexistent_order_id, status=StripeLikeEvent.PAYMENT_SUCCEEDED
    )
    body = json.dumps(payload).encode()
    signature = sign_stripe_like(body, STRIPE_LIKE_SECRET)

    response = payhub_client.send_webhook(
        Provider.STRIPE_LIKE, payload, headers={Headers.SIGNATURE: signature}
    )

    assert response.status_code == 202

    def order_message_present() -> bool:
        messages = sqs_client["outbound"].receive_messages()
        return any(json.loads(m["Body"]).get("order_id") == nonexistent_order_id for m in messages)

    with pytest.raises(TimeoutError):
        smart_wait(function=order_message_present, expected_result=lambda present: present, timeout=3)

    assert not order_message_present()
