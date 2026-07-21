import asyncio
import base64
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Order
from src.db.session import async_session_maker
from src.pipeline.process_webhook import process_webhook_message
from src.providers.registry import PROVIDERS
from src.queue.sqs import SQSQueue
from src.settings import settings

logger = logging.getLogger(__name__)

inbound_queue = SQSQueue(settings.inbound_queue_name)
outbound_queue = SQSQueue(settings.outbound_queue_name)


async def handle_message(
    message: dict,
    session: AsyncSession,
    outbound_queue: SQSQueue,
    process_fn=process_webhook_message,
) -> tuple[str, dict]:
    """Process one message; returns (action, message) where action is
    "processed", "requeue", or "hold". retry_count lives on the message
    itself so a re-queued attempt doesn't depend on the DB being reachable.
    """
    try:
        await process_fn(message, session, outbound_queue)
        return "processed", message
    except Exception:
        logger.exception("transient failure processing webhook message")
        retry_count = message.get("retry_count", 0) + 1
        message = {**message, "retry_count": retry_count}
        if retry_count >= settings.max_provider_retries:
            await _hold_order(message, session, outbound_queue)
            return "hold", message
        return "requeue", message


async def _hold_order(message: dict, session: AsyncSession, outbound_queue: SQSQueue) -> None:
    try:
        adapter = PROVIDERS[message["provider"]]
        raw_body = base64.b64decode(message["raw_body"])
        normalized = adapter.parser.parse(raw_body)
    except Exception:
        logger.exception("could not identify order to hold after retry exhaustion")
        return

    order = await session.get(Order, normalized.order_id)
    if order is None:
        return

    order.status = "HOLD"
    order.retry_count = message["retry_count"]
    await session.commit()
    await outbound_queue.send(
        {"order_id": order.id, "status": order.status, "provider": order.provider}
    )


async def run() -> None:
    while True:
        raw_messages = await inbound_queue.receive(max_messages=10, wait_seconds=10)
        for raw_message in raw_messages:
            body = json.loads(raw_message["Body"])
            async with async_session_maker() as session:
                action, updated = await handle_message(body, session, outbound_queue)

            if action == "requeue":
                delay = int(settings.retry_backoff_seconds * 2 ** updated["retry_count"])
                await inbound_queue.send(updated, delay_seconds=delay)

            await inbound_queue.delete(raw_message["ReceiptHandle"])


if __name__ == "__main__":
    asyncio.run(run())
