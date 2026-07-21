from collections.abc import Callable
from typing import Any

import requests


class BaseHttpClient:
    def __init__(self, scheme: str, host: str, port: int, version: str = "v1") -> None:
        self.base_url = f"{scheme}://{host}:{port}/api/{version}"
        self.session = requests.Session()

    def build_url(self, endpoint: str, entity_id: Any = None, action: str | None = None) -> str:
        parts = [self.base_url, endpoint]
        if entity_id is not None:
            parts.append(str(entity_id))
        if action is not None:
            parts.append(action)
        return "/".join(parts)

    def get(
        self,
        url: str,
        params: dict | None = None,
        wrapper: Callable[[requests.Response], Any] | None = None,
    ) -> Any:
        response = self.session.get(url, params=params)
        return wrapper(response) if wrapper else response

    def post(
        self,
        url: str,
        json: dict | None = None,
        data: bytes | None = None,
        headers: dict | None = None,
        wrapper: Callable[[requests.Response], Any] | None = None,
    ) -> Any:
        response = self.session.post(url, json=json, data=data, headers=headers)
        return wrapper(response) if wrapper else response
