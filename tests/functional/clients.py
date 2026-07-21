import json

import requests

from api_wrappers import PayhubWrappers
from constants import Routes
from models import OrderResponse
from qa_toolkit.base_http_client import BaseHttpClient
from qa_toolkit.waiter import smart_wait


class PayhubClient(BaseHttpClient):
    def __init__(self, host: str, port: int) -> None:
        super().__init__(scheme="http", host=host, port=port, version="v1")
        self._wrappers = PayhubWrappers()

    def create_order(
        self, product_id: str, provider: str, amount: str, currency: str = "USD"
    ) -> OrderResponse:
        url = self.build_url(Routes.ORDERS)
        body = {
            "product_id": product_id,
            "provider": provider,
            "amount": amount,
            "currency": currency,
        }
        return self.post(url, json=body, wrapper=self._wrappers.wrap_order)

    def get_order(self, order_id: int) -> OrderResponse:
        url = self.build_url(Routes.ORDERS, entity_id=order_id)
        return self.get(url, wrapper=self._wrappers.wrap_order)

    def send_webhook(
        self, provider: str, payload: dict, headers: dict | None = None
    ) -> requests.Response:
        url = self.build_url(Routes.WEBHOOKS, entity_id=provider)
        return self.post(url, data=json.dumps(payload).encode(), headers=headers)

    def wait_order_in_status(self, order_id: int, status: str, timeout: float = 10) -> OrderResponse:
        return smart_wait(
            function=lambda: self.get_order(order_id),
            expected_result=lambda order: order.status == status,
            timeout=timeout,
        )

    def ping(self) -> dict:
        url = f"{self.base_url.rsplit('/api/', 1)[0]}/ping"
        return self.session.get(url).json()
