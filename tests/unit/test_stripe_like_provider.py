import json
from decimal import Decimal

import pytest

from src.providers.base import SignatureVerificationError
from src.providers.stripe_like.parser import StripeLikeParser
from src.providers.stripe_like.verifier import StripeLikeVerifier
from tests.unit.conftest import STRIPE_LIKE_SECRET, sign_stripe_like


def _payload(event: str = "payment_succeeded") -> dict:
    return {
        "order_id": 123,
        "transaction_id": "tx_abc",
        "event": event,
        "amount": "19.99",
        "currency": "USD",
    }


class TestStripeLikeVerifier:
    def test_accepts_correctly_signed_body(self) -> None:
        verifier = StripeLikeVerifier(STRIPE_LIKE_SECRET)
        raw_body = json.dumps(_payload()).encode()
        signature = sign_stripe_like(raw_body)

        verifier.verify(raw_body, {"X-Signature": signature})

    def test_rejects_tampered_body(self) -> None:
        verifier = StripeLikeVerifier(STRIPE_LIKE_SECRET)
        raw_body = json.dumps(_payload()).encode()
        signature = sign_stripe_like(raw_body)
        tampered_body = json.dumps(_payload(event="payment_failed")).encode()

        with pytest.raises(SignatureVerificationError):
            verifier.verify(tampered_body, {"X-Signature": signature})

    def test_rejects_missing_header(self) -> None:
        verifier = StripeLikeVerifier(STRIPE_LIKE_SECRET)
        raw_body = json.dumps(_payload()).encode()

        with pytest.raises(SignatureVerificationError):
            verifier.verify(raw_body, {})


class TestStripeLikeParser:
    def test_parses_payment_succeeded(self) -> None:
        parser = StripeLikeParser()
        raw_body = json.dumps(_payload(event="payment_succeeded")).encode()

        normalized = parser.parse(raw_body)

        assert normalized.order_id == 123
        assert normalized.provider_transaction_id == "tx_abc"
        assert normalized.status == "paid"
        assert normalized.amount == Decimal("19.99")
        assert normalized.currency == "USD"

    def test_parses_payment_failed(self) -> None:
        parser = StripeLikeParser()
        raw_body = json.dumps(_payload(event="payment_failed")).encode()

        normalized = parser.parse(raw_body)

        assert normalized.status == "failed"
