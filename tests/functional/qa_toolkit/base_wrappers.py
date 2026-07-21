from typing import Any

from pydantic import BaseModel
from requests import Response


class ErrorResponse(BaseModel):
    detail: str


class BaseWrapper:
    """Default wrappers shared by all API clients."""

    @staticmethod
    def wrap_json(response: Response) -> Any:
        try:
            return response.json()
        except ValueError:
            raise ValueError(f"Invalid JSON response: {response.text}")

    @staticmethod
    def wrap_raw_response(response: Response) -> Response:
        return response

    @staticmethod
    def wrap_204(response: Response) -> None:
        if response.status_code != 204:
            raise ValueError(f"Expected 204 status code, got {response.status_code}")
        return None

    @staticmethod
    def handle_error_response(response: Response, status_code: int) -> ErrorResponse:
        if response.status_code != status_code:
            raise ValueError(f"Expected status code {status_code}, got {response.status_code}")
        return ErrorResponse(**response.json())

    @staticmethod
    def wrap_400(response: Response) -> ErrorResponse:
        return BaseWrapper.handle_error_response(response, status_code=400)

    @staticmethod
    def wrap_404(response: Response) -> ErrorResponse:
        return BaseWrapper.handle_error_response(response, status_code=404)

    @staticmethod
    def wrap_422(response: Response) -> ErrorResponse:
        return BaseWrapper.handle_error_response(response, status_code=422)
