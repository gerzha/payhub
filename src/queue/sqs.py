import json

import aioboto3

from src.settings import settings


class SQSQueue:
    def __init__(self, queue_name: str) -> None:
        self._queue_name = queue_name
        self._session = aioboto3.Session()

    async def _get_queue_url(self, client) -> str:
        response = await client.get_queue_url(QueueName=self._queue_name)
        return response["QueueUrl"]

    async def send(self, body: dict, delay_seconds: int = 0) -> None:
        async with self._session.client(
            "sqs", endpoint_url=settings.sqs_endpoint_url
        ) as client:
            queue_url = await self._get_queue_url(client)
            await client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(body),
                DelaySeconds=delay_seconds,
            )

    async def receive(self, max_messages: int = 10, wait_seconds: int = 10) -> list[dict]:
        async with self._session.client(
            "sqs", endpoint_url=settings.sqs_endpoint_url
        ) as client:
            queue_url = await self._get_queue_url(client)
            response = await client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_seconds,
            )
            return response.get("Messages", [])

    async def delete(self, receipt_handle: str) -> None:
        async with self._session.client(
            "sqs", endpoint_url=settings.sqs_endpoint_url
        ) as client:
            queue_url = await self._get_queue_url(client)
            await client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
