import requests

from models import OrderResponse
from qa_toolkit.base_wrappers import BaseWrapper


class PayhubWrappers(BaseWrapper):
    @staticmethod
    def wrap_order(response: requests.Response) -> OrderResponse:
        assert response.status_code in (200, 201), response.text
        return OrderResponse.model_validate(response.json())
