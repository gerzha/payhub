import hashlib
import hmac
from collections.abc import Mapping

from src.providers.base import SignatureVerificationError


class StripeLikeVerifier:
    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()

    def verify(self, raw_body: bytes, headers: Mapping[str, str]) -> None:
        lowercased_headers = {key.lower(): value for key, value in headers.items()}
        signature = lowercased_headers.get("x-signature")
        if signature is None:
            raise SignatureVerificationError("missing X-Signature header")

        expected = hmac.new(self._secret, raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise SignatureVerificationError("signature mismatch")
