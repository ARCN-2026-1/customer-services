from urllib.parse import quote_plus

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CustomerServiceSettings(BaseSettings):
    database_url: str | None = None
    db_host: str | None = None
    db_port: int = 3306
    db_user: str | None = None
    db_password: str | None = None
    db_name: str | None = None
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 1800
    event_publisher_backend: str = "rabbitmq"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/%2F"
    rabbitmq_input_queue: str = "customer.validation.requests"
    rabbitmq_request_exchange: str = "customer.exchange"
    rabbitmq_request_routing_key: str = "customer.request"
    rabbitmq_response_exchange: str = "customer.exchange"
    rabbitmq_response_routing_key: str = "customer.response.key"

    @field_validator("event_publisher_backend")
    @classmethod
    def validate_event_publisher_backend(cls, value: str) -> str:
        if value not in {"rabbitmq", "in-memory"}:
            raise ValueError(
                "event_publisher_backend must be 'rabbitmq' or 'in-memory'"
            )
        return value

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        required_values = {
            "DB_HOST": self.db_host,
            "DB_USER": self.db_user,
            "DB_PASSWORD": self.db_password,
            "DB_NAME": self.db_name,
        }
        missing_values = [name for name, value in required_values.items() if not value]
        if missing_values:
            missing_values_text = ", ".join(sorted(missing_values))
            raise ValueError(
                f"Missing MySQL configuration values: {missing_values_text}"
            )

        return (
            "mysql+pymysql://"
            f"{quote_plus(self.db_user or '')}:{quote_plus(self.db_password or '')}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    model_config = SettingsConfigDict(env_prefix="CUSTOMER_SERVICE_")
