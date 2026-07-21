from dataclasses import dataclass

from src.providers.base import Parser, Verifier
from src.providers.paypal_like.parser import PaypalLikeParser
from src.providers.paypal_like.verifier import PaypalLikeVerifier
from src.providers.stripe_like.parser import StripeLikeParser
from src.providers.stripe_like.verifier import StripeLikeVerifier
from src.settings import settings


@dataclass(frozen=True)
class ProviderAdapter:
    verifier: Verifier
    parser: Parser


PROVIDERS: dict[str, ProviderAdapter] = {
    "stripe_like": ProviderAdapter(
        verifier=StripeLikeVerifier(settings.stripe_like_secret),
        parser=StripeLikeParser(),
    ),
    "paypal_like": ProviderAdapter(
        verifier=PaypalLikeVerifier(settings.paypal_like_secret),
        parser=PaypalLikeParser(),
    ),
}
