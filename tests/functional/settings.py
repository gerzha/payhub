import os

PAYHUB_HOST = os.environ.get("PAYHUB_HOST", "localhost")
PAYHUB_PORT = int(os.environ.get("PAYHUB_PORT", "8000"))

WIREMOCK_HOST = os.environ.get("WIREMOCK_HOST", "localhost")
WIREMOCK_PORT = int(os.environ.get("WIREMOCK_PORT", "8080"))

LOCALSTACK_ENDPOINT_URL = os.environ.get("LOCALSTACK_ENDPOINT_URL", "http://localhost:4566")

INBOUND_QUEUE_NAME = os.environ.get("PAYHUB_INBOUND_QUEUE_NAME", "payhub-inbound-webhooks")
OUTBOUND_QUEUE_NAME = os.environ.get("PAYHUB_OUTBOUND_QUEUE_NAME", "payhub-outbound-status")

STRIPE_LIKE_SECRET = os.environ.get("PAYHUB_STRIPE_LIKE_SECRET", "stripe_like_dev_secret")
PAYPAL_LIKE_SECRET = os.environ.get("PAYHUB_PAYPAL_LIKE_SECRET", "paypal_like_dev_secret")
