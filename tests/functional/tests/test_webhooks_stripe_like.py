import json

import pytest

from clients import PayhubClient
from constants import OrderStatus, Provider
from mocks.stripe_like_processing import sign_stripe_like, stripe_like_webhook_payload
from qa_toolkit.waiter import smart_wait
from settings import STRIPE_LIKE_SECRET


def _send_signed_webhook(payhub_client: PayhubClient, order_id: int, status: str) -> None:
    payload = stripe_like_webhook_payload(order_id=order_id, status=status)
    body = json.dumps(payload).encode()
    signature = sign_stripe_like(body, STRIPE_LIKE_SECRET)
    payhub_client.send_webhook(
        Provider.STRIPE_LIKE, payload, headers={"X-Signature": signature}
    )


def test_webhook_payment_succeeded_moves_order_to_paid(payhub_client, make_order, sqs_client) -> None:
    order = make_order(provider=Provider.STRIPE_LIKE)

    _send_signed_webhook(payhub_client, order.id, "payment_succeeded")

    updated = payhub_client.wait_order_in_status(order.id, OrderStatus.PAID)
    assert updated.status == OrderStatus.PAID

    messages = sqs_client["outbound"].receive_messages()
    assert any(
        _matches_status_event(m, order.id, OrderStatus.PAID) for m in messages
    )


def test_webhook_payment_failed_moves_order_to_failed(payhub_client, make_order, sqs_client) -> None:
    order = make_order(provider=Provider.STRIPE_LIKE)

    _send_signed_webhook(payhub_client, order.id, "payment_failed")

    updated = payhub_client.wait_order_in_status(order.id, OrderStatus.FAILED)
    assert updated.status == OrderStatus.FAILED


def test_webhook_invalid_signature_moves_order_to_failed(payhub_client, make_order) -> None:
    order = make_order(provider=Provider.STRIPE_LIKE)
    payload = stripe_like_webhook_payload(order_id=order.id, status="payment_succeeded")

    payhub_client.send_webhook(
        Provider.STRIPE_LIKE, payload, headers={"X-Signature": "garbage-signature"}
    )

    updated = payhub_client.wait_order_in_status(order.id, OrderStatus.FAILED)
    assert updated.status == OrderStatus.FAILED


def test_duplicate_webhook_is_idempotent(payhub_client, make_order, sqs_client) -> None:
    order = make_order(provider=Provider.STRIPE_LIKE)

    _send_signed_webhook(payhub_client, order.id, "payment_succeeded")
    payhub_client.wait_order_in_status(order.id, OrderStatus.PAID)

    _send_signed_webhook(payhub_client, order.id, "payment_succeeded")

    with pytest.raises(TimeoutError):
        smart_wait(
            function=lambda: sqs_client["outbound"].receive_messages(),
            expected_result=lambda messages: any(
                _matches_status_event(m, order.id, OrderStatus.PAID) for m in messages
            ),
            timeout=3,
        )

    messages = sqs_client["outbound"].receive_messages()
    status_events = [m for m in messages if _matches_status_event(m, order.id, OrderStatus.PAID)]
    assert len(status_events) == 1


def _matches_status_event(message: dict, order_id: int, status: str) -> bool:
    body = json.loads(message["Body"])
    return body.get("order_id") == order_id and body.get("status") == status
