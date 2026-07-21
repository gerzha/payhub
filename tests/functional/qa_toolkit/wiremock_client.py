import requests


class WiremockClient:
    def __init__(self, host: str, port: int) -> None:
        self._admin_url = f"http://{host}:{port}/__admin"

    def create_stub(self, request_matcher: dict, response: dict) -> str:
        mapping = {"request": request_matcher, "response": response}
        resp = requests.post(f"{self._admin_url}/mappings", json=mapping)
        resp.raise_for_status()
        return resp.json()["id"]

    def delete_stub(self, stub_id: str) -> None:
        requests.delete(f"{self._admin_url}/mappings/{stub_id}").raise_for_status()

    def clear_history(self) -> None:
        requests.delete(f"{self._admin_url}/requests").raise_for_status()

    def find_requests(self, url_pattern: str, method: str = "ANY") -> list[dict]:
        criteria = {"method": method, "urlPathPattern": url_pattern}
        resp = requests.post(f"{self._admin_url}/requests/find", json=criteria)
        resp.raise_for_status()
        return resp.json()["requests"]
