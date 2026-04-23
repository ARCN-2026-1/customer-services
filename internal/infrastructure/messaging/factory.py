from __future__ import annotations

from typing import Any

from internal.infrastructure.config.settings import CustomerServiceSettings
from internal.infrastructure.messaging.in_memory_event_publisher import (
    InMemoryEventPublisher,
)
from internal.infrastructure.messaging.rabbitmq_customer_validation_consumer import (
    RabbitMQCustomerValidationConsumer,
)
from internal.infrastructure.messaging.rabbitmq_event_publisher import (
    RabbitMQEventPublisher,
)
from internal.interfaces.messaging.customer_validation_consumer import (
    CustomerValidationConsumer,
)

_CONNECTION_FACTORIES_BY_SETTINGS: dict[int, Any] = {}


def create_event_publisher(settings: CustomerServiceSettings) -> Any:
    if settings.event_publisher_backend == "rabbitmq":
        connection_factory = create_rabbitmq_connection_factory(settings)
        return RabbitMQEventPublisher(
            connection_factory=connection_factory,
            exchange_name=settings.rabbitmq_response_exchange,
            routing_key=settings.rabbitmq_response_routing_key,
        )
    if settings.event_publisher_backend == "in-memory":
        return InMemoryEventPublisher()
    raise ValueError(
        f"Unsupported event publisher backend: {settings.event_publisher_backend}"
    )


def create_customer_validation_consumer(
    *,
    settings: CustomerServiceSettings,
    handler: CustomerValidationConsumer,
    event_publisher: Any,
) -> RabbitMQCustomerValidationConsumer:
    return RabbitMQCustomerValidationConsumer(
        connection_factory=create_rabbitmq_connection_factory(settings),
        request_exchange=settings.rabbitmq_request_exchange,
        request_routing_key=settings.rabbitmq_request_routing_key,
        input_queue=settings.rabbitmq_input_queue,
        handler=handler,
        event_publisher=event_publisher,
    )


def create_rabbitmq_connection_factory(
    settings: CustomerServiceSettings,
) -> Any:
    settings_key = id(settings)
    if settings_key not in _CONNECTION_FACTORIES_BY_SETTINGS:
        _CONNECTION_FACTORIES_BY_SETTINGS[settings_key] = lambda: (
            open_rabbitmq_connection(
                settings.rabbitmq_url,
                heartbeat=60,
                blocked_connection_timeout=30,
            )
        )
    return _CONNECTION_FACTORIES_BY_SETTINGS[settings_key]


def open_rabbitmq_connection(
    url: str,
    *,
    heartbeat: int,
    blocked_connection_timeout: int,
) -> Any:
    import pika

    parameters = pika.URLParameters(url)
    parameters.heartbeat = heartbeat
    parameters.blocked_connection_timeout = blocked_connection_timeout
    return pika.BlockingConnection(parameters)
