import requests

from models import OrderResponse


class PayhubWrappers:
    def wrap_order(self, response: requests.Response) -> OrderResponse:
        assert response.status_code in (200, 201), response.text
        return OrderResponse.model_validate(response.json())

    def wrap_raw(self, response: requests.Response) -> requests.Response:
        return response
