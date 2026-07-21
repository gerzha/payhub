import pytest

from clients import PayhubClient
from constants import Provider
from qa_toolkit.sqs_client import SQSClient
from settings import (
    INBOUND_QUEUE_NAME,
    LOCALSTACK_ENDPOINT_URL,
    OUTBOUND_QUEUE_NAME,
    PAYHUB_HOST,
    PAYHUB_PORT,
)


@pytest.fixture
def payhub_client() -> PayhubClient:
    return PayhubClient(host=PAYHUB_HOST, port=PAYHUB_PORT)


@pytest.fixture
def sqs_client(request: pytest.FixtureRequest) -> dict[str, SQSClient]:
    clients = {
        "inbound": SQSClient(LOCALSTACK_ENDPOINT_URL, INBOUND_QUEUE_NAME),
        "outbound": SQSClient(LOCALSTACK_ENDPOINT_URL, OUTBOUND_QUEUE_NAME),
    }

    def _purge() -> None:
        for client in clients.values():
            client.purge_queue()

    request.addfinalizer(_purge)
    return clients


@pytest.fixture
def make_order(payhub_client: PayhubClient):
    def _make(provider: str = Provider.STRIPE_LIKE, amount: str = "19.99"):
        return payhub_client.create_order(
            product_id="test-product", provider=provider, amount=amount
        )

    return _make
