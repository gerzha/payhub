from collections.abc import Mapping
from typing import Protocol

from src.schemas.webhook import NormalizedWebhook


class SignatureVerificationError(Exception):
    pass


class Verifier(Protocol):
    def verify(self, raw_body: bytes, headers: Mapping[str, str]) -> None:
        """Raises SignatureVerificationError on failure."""
        ...


class Parser(Protocol):
    def parse(self, raw_body: bytes) -> NormalizedWebhook: ...
