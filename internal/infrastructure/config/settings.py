from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CustomerServiceSettings(BaseSettings):
    database_url: str = "sqlite:///./data/customer-service.sqlite"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 1800
    event_publisher_backend: str = "rabbitmq"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/%2F"
    rabbitmq_exchange: str = "customer.events"
    rabbitmq_input_queue: str = "customer.validation.requests"
    rabbitmq_consumer_exchange: str = "booking.events"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("sqlite"):
            raise ValueError(
                "Customer service persistence is SQLite-only in this batch"
            )
        return value

    @field_validator("event_publisher_backend")
    @classmethod
    def validate_event_publisher_backend(cls, value: str) -> str:
        if value not in {"rabbitmq", "in-memory"}:
            raise ValueError(
                "event_publisher_backend must be 'rabbitmq' or 'in-memory'"
            )
        return value

    model_config = SettingsConfigDict(env_prefix="CUSTOMER_SERVICE_")
