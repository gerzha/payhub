from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PAYHUB_")

    database_url: str = "postgresql+asyncpg://payhub:payhub@localhost:5432/payhub"
    sqs_endpoint_url: str = "http://localhost:4566"
    inbound_queue_name: str = "payhub-inbound-webhooks"
    outbound_queue_name: str = "payhub-outbound-status"
    stripe_like_secret: str = "stripe_like_dev_secret"
    paypal_like_secret: str = "paypal_like_dev_secret"
    max_provider_retries: int = 5
    retry_backoff_seconds: float = 1.0


settings = Settings()
