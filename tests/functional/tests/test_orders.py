from clients import PayhubClient
from constants import OrderStatus, Provider


def test_ping(payhub_client: PayhubClient) -> None:
    assert payhub_client.ping() == {"status": "pong"}


def test_create_order_returns_pending(payhub_client: PayhubClient) -> None:
    order = payhub_client.create_order(
        product_id="test-product", provider=Provider.STRIPE_LIKE, amount="19.99"
    )

    assert order.status == OrderStatus.PENDING
    assert order.product_id == "test-product"
    assert order.provider == Provider.STRIPE_LIKE


def test_get_order_not_found(payhub_client: PayhubClient) -> None:
    response = payhub_client.get(payhub_client.build_url("orders", entity_id=999999))

    assert response.status_code == 404
