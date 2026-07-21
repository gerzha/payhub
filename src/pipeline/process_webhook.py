import base64
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Order
from src.providers.base import SignatureVerificationError
from src.providers.registry import PROVIDERS, ProviderAdapter
from src.queue.sqs import SQSQueue

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {"PAID", "FAILED"}
_WEBHOOK_STATUS_TO_ORDER_STATUS = {"paid": "PAID", "failed": "FAILED"}


async def process_webhook_message(
    message: dict, session: AsyncSession, outbound_queue: SQSQueue
) -> None:
    provider_name = message["provider"]
    raw_body = base64.b64decode(message["raw_body"])
    headers = message["headers"]
    adapter = PROVIDERS[provider_name]

    try:
        adapter.verifier.verify(raw_body, headers)
    except SignatureVerificationError:
        await _handle_invalid_signature(adapter, provider_name, raw_body, session, outbound_queue)
        return

    try:
        normalized = adapter.parser.parse(raw_body)
    except Exception:
        logger.info("dropping unparsable %s webhook payload", provider_name)
        return

    order = await session.get(Order, normalized.order_id)
    if order is None:
        logger.info("dropping webhook for unknown order_id=%s", normalized.order_id)
        return

    if order.status in _TERMINAL_STATUSES:
        logger.info("dropping duplicate webhook for order_id=%s", order.id)
        return

    order.status = _WEBHOOK_STATUS_TO_ORDER_STATUS[normalized.status]
    order.provider_transaction_id = normalized.provider_transaction_id
    await session.commit()

    await _publish_status_changed(order, outbound_queue)


async def _handle_invalid_signature(
    adapter: ProviderAdapter,
    provider_name: str,
    raw_body: bytes,
    session: AsyncSession,
    outbound_queue: SQSQueue,
) -> None:
    try:
        normalized = adapter.parser.parse(raw_body)
    except Exception:
        logger.info("invalid signature for unparsable %s webhook, dropping", provider_name)
        return

    order = await session.get(Order, normalized.order_id)
    if order is None or order.status in _TERMINAL_STATUSES:
        return

    order.status = "FAILED"
    await session.commit()
    await _publish_status_changed(order, outbound_queue)


async def _publish_status_changed(order: Order, outbound_queue: SQSQueue) -> None:
    await outbound_queue.send(
        {"order_id": order.id, "status": order.status, "provider": order.provider}
    )
