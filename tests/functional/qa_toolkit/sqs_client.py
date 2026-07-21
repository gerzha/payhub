import json

import boto3


class SQSClient:
    def __init__(self, endpoint_url: str, queue_name: str) -> None:
        self._client = boto3.client("sqs", endpoint_url=endpoint_url, region_name="us-east-1")
        self._queue_url = self._client.get_queue_url(QueueName=queue_name)["QueueUrl"]

    def send_message(self, body: dict) -> None:
        self._client.send_message(QueueUrl=self._queue_url, MessageBody=json.dumps(body))

    def receive_messages(self, max_messages: int = 10, wait_seconds: int = 2) -> list[dict]:
        response = self._client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_seconds,
        )
        return response.get("Messages", [])

    def delete_message(self, receipt_handle: str) -> None:
        self._client.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt_handle)

    def purge_queue(self) -> None:
        try:
            self._client.purge_queue(QueueUrl=self._queue_url)
        except self._client.exceptions.PurgeQueueInProgress:
            pass
