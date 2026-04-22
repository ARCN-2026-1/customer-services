from __future__ import annotations

from typing import Any

from internal.infrastructure.config.settings import CustomerServiceSettings
from internal.infrastructure.messaging.in_memory_event_publisher import (
    InMemoryEventPublisher,
)
from internal.infrastructure.messaging.rabbitmq_event_publisher import (
    RabbitMQEventPublisher,
)


def create_event_publisher(settings: CustomerServiceSettings) -> Any:
    if settings.event_publisher_backend == "rabbitmq":
        return RabbitMQEventPublisher(
            connection_factory=lambda: open_rabbitmq_connection(
                settings.rabbitmq_url,
                heartbeat=60,
                blocked_connection_timeout=30,
            ),
            exchange_name=settings.rabbitmq_exchange,
        )
    if settings.event_publisher_backend == "in-memory":
        return InMemoryEventPublisher()
    raise ValueError(
        f"Unsupported event publisher backend: {settings.event_publisher_backend}"
    )


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
