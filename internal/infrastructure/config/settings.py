from urllib.parse import quote_plus

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALEMBIC_INI_DEFAULT_DATABASE_URL = (
    "mysql+pymysql://customer:secret@localhost:3306/customer_service?charset=utf8mb4"
)


class CustomerServiceSettings(BaseSettings):
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("CUSTOMER_SERVICE_LOG_LEVEL", "LOG_LEVEL"),
    )
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CUSTOMER_SERVICE_DATABASE_URL", "DATABASE_URL"),
    )
    db_host: str | None = Field(
        default="localhost",
        validation_alias=AliasChoices(
            "CUSTOMER_SERVICE_DB_HOST", "DB_HOST", "MYSQL_HOST"
        ),
    )
    db_port: int = Field(
        default=3306,
        validation_alias=AliasChoices(
            "CUSTOMER_SERVICE_DB_PORT", "DB_PORT", "MYSQL_LOCAL_PORT"
        ),
    )
    db_user: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CUSTOMER_SERVICE_DB_USER",
            "DB_USER",
            "MYSQL_USER",
        ),
    )
    db_password: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CUSTOMER_SERVICE_DB_PASSWORD", "DB_PASSWORD", "MYSQL_PASSWORD"
        ),
    )
    db_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CUSTOMER_SERVICE_DB_NAME",
            "DB_NAME",
            "MYSQL_DATABASE",
        ),
    )
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 1800
    event_publisher_backend: str = "rabbitmq"
    rabbitmq_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CUSTOMER_SERVICE_RABBITMQ_URL", "RABBITMQ_URL"),
    )
    rabbitmq_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices(
            "CUSTOMER_SERVICE_RABBITMQ_HOST",
            "RABBITMQ_HOST",
        ),
    )
    rabbitmq_port: int = Field(
        default=5672,
        validation_alias=AliasChoices(
            "CUSTOMER_SERVICE_RABBITMQ_PORT",
            "RABBITMQ_PORT",
        ),
    )
    rabbitmq_user: str = Field(
        default="guest",
        validation_alias=AliasChoices(
            "CUSTOMER_SERVICE_RABBITMQ_USER",
            "RABBITMQ_USER",
            "RABBITMQ_DEFAULT_USER",
        ),
    )
    rabbitmq_password: str = Field(
        default="guest",
        validation_alias=AliasChoices(
            "CUSTOMER_SERVICE_RABBITMQ_PASSWORD",
            "RABBITMQ_PASSWORD",
            "RABBITMQ_DEFAULT_PASS",
        ),
    )
    rabbitmq_input_queue: str = "customer.validation.requests"
    rabbitmq_request_exchange: str = "customer.exchange"
    rabbitmq_request_exchange_type: str = "direct"
    rabbitmq_request_routing_key: str = "customer.request"
    rabbitmq_response_exchange: str = "customer.exchange"
    rabbitmq_response_exchange_type: str = "direct"
    rabbitmq_response_routing_key: str = "customer.response.key"

    @field_validator("event_publisher_backend")
    @classmethod
    def validate_event_publisher_backend(cls, value: str) -> str:
        if value not in {"rabbitmq", "in-memory"}:
            raise ValueError(
                "event_publisher_backend must be 'rabbitmq' or 'in-memory'"
            )
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized_value = value.upper()
        if normalized_value == "WARN":
            normalized_value = "WARNING"

        if normalized_value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(
                "log_level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )

        return normalized_value

    @field_validator(
        "rabbitmq_request_exchange_type",
        "rabbitmq_response_exchange_type",
    )
    @classmethod
    def validate_exchange_type(cls, value: str) -> str:
        if value not in {"direct", "topic", "fanout", "headers"}:
            raise ValueError(
                "rabbitmq exchange type must be one of direct, topic, fanout, headers"
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

    @property
    def resolved_rabbitmq_url(self) -> str:
        if self.rabbitmq_url:
            return self.rabbitmq_url

        return (
            "amqp://"
            f"{quote_plus(self.rabbitmq_user)}:{quote_plus(self.rabbitmq_password)}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/%2F"
        )

    model_config = SettingsConfigDict(
        env_prefix="CUSTOMER_SERVICE_",
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


def resolve_alembic_database_url(configured_url: str | None) -> str:
    if configured_url and configured_url != ALEMBIC_INI_DEFAULT_DATABASE_URL:
        return configured_url

    return CustomerServiceSettings().resolved_database_url


def escape_for_alembic_config(database_url: str) -> str:
    return database_url.replace("%", "%%")
