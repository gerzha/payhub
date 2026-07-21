import base64
import json
from unittest.mock import AsyncMock

from src.db.models import Order
from src.settings import settings
from src.worker.order_worker import handle_message


def _message() -> dict:
    payload = {
        "order_id": 123,
        "transaction_id": "tx_abc",
        "event": "payment_succeeded",
        "amount": "19.99",
        "currency": "USD",
    }
    return {
        "provider": "stripe_like",
        "raw_body": base64.b64encode(json.dumps(payload).encode()).decode(),
        "headers": {},
    }


class TestHandleMessageRetries:
    async def test_requeues_with_incrementing_retry_count_below_budget(self) -> None:
        failing_process = AsyncMock(side_effect=RuntimeError("db connection error"))
        session = AsyncMock()
        outbound_queue = AsyncMock()

        action, updated = await handle_message(
            _message(), session, outbound_queue, process_fn=failing_process
        )

        assert action == "requeue"
        assert updated["retry_count"] == 1

    async def test_holds_order_after_retry_budget_exhausted(self) -> None:
        failing_process = AsyncMock(side_effect=RuntimeError("db connection error"))
        session = AsyncMock()
        order = Order(id=123, product_id="p1", provider="stripe_like", status="PROCESSING", amount=19.99, currency="USD")
        session.get = AsyncMock(return_value=order)
        outbound_queue = AsyncMock()

        message = _message()
        message["retry_count"] = settings.max_provider_retries - 1

        action, updated = await handle_message(
            message, session, outbound_queue, process_fn=failing_process
        )

        assert action == "hold"
        assert updated["retry_count"] == settings.max_provider_retries
        assert order.status == "HOLD"
        outbound_queue.send.assert_awaited_once()

    async def test_processed_when_no_exception(self) -> None:
        ok_process = AsyncMock(return_value=None)
        session = AsyncMock()
        outbound_queue = AsyncMock()

        action, updated = await handle_message(
            _message(), session, outbound_queue, process_fn=ok_process
        )

        assert action == "processed"
        assert "retry_count" not in updated
