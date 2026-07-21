import hashlib
import hmac
import json
from collections.abc import Mapping

from src.providers.base import SignatureVerificationError

CANONICAL_JSON_KWARGS: dict = {"sort_keys": True, "separators": (",", ":")}


class PaypalLikeVerifier:
    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()

    def verify(self, raw_body: bytes, headers: Mapping[str, str]) -> None:
        payload = json.loads(raw_body)
        signature = payload.get("signature")
        if signature is None:
            raise SignatureVerificationError("missing signature field")

        unsigned = {k: v for k, v in payload.items() if k != "signature"}
        canonical = json.dumps(unsigned, **CANONICAL_JSON_KWARGS).encode()
        expected = hmac.new(self._secret, canonical, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise SignatureVerificationError("signature mismatch")
