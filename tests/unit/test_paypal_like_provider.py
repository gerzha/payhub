import json
from decimal import Decimal

import pytest

from src.providers.base import SignatureVerificationError
from src.providers.paypal_like.parser import PaypalLikeParser
from src.providers.paypal_like.verifier import PaypalLikeVerifier
from tests.unit.conftest import PAYPAL_LIKE_SECRET, build_paypal_like_body


def _resource(state: str = "COMPLETED") -> dict:
    return {
        "order_id": 123,
        "txn_id": "PAY-xyz",
        "state": state,
        "value": "19.99",
        "currency_code": "USD",
    }


class TestPaypalLikeVerifier:
    def test_accepts_correctly_signed_body(self) -> None:
        verifier = PaypalLikeVerifier(PAYPAL_LIKE_SECRET)
        raw_body = build_paypal_like_body(_resource())

        verifier.verify(raw_body, {})

    def test_rejects_tampered_body(self) -> None:
        verifier = PaypalLikeVerifier(PAYPAL_LIKE_SECRET)
        raw_body = build_paypal_like_body(_resource())
        payload = json.loads(raw_body)
        payload["resource"]["state"] = "DENIED"
        tampered_body = json.dumps(payload).encode()

        with pytest.raises(SignatureVerificationError):
            verifier.verify(tampered_body, {})

    def test_rejects_missing_signature_field(self) -> None:
        verifier = PaypalLikeVerifier(PAYPAL_LIKE_SECRET)
        raw_body = json.dumps({"resource": _resource()}).encode()

        with pytest.raises(SignatureVerificationError):
            verifier.verify(raw_body, {})


class TestPaypalLikeParser:
    def test_parses_completed(self) -> None:
        parser = PaypalLikeParser()
        raw_body = build_paypal_like_body(_resource(state="COMPLETED"))

        normalized = parser.parse(raw_body)

        assert normalized.order_id == 123
        assert normalized.provider_transaction_id == "PAY-xyz"
        assert normalized.status == "paid"
        assert normalized.amount == Decimal("19.99")
        assert normalized.currency == "USD"

    def test_parses_denied(self) -> None:
        parser = PaypalLikeParser()
        raw_body = build_paypal_like_body(_resource(state="DENIED"))

        normalized = parser.parse(raw_body)

        assert normalized.status == "failed"
