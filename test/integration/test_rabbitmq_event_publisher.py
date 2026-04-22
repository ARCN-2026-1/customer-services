import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pika
import pytest
from testcontainers.rabbitmq import RabbitMqContainer

from internal.domain.events.customer_events import (
    CustomerInfoUpdated,
    CustomerRegistered,
)
from internal.infrastructure.messaging.rabbitmq_event_publisher import (
    RabbitMQEventPublisher,
)


def test_When_PublishingLifecycleEventsToRealRabbitMq_Expect_ConsumedMessagesMatchDomainContract() -> (  # noqa: E501
    None
):
    # Arrange
    _require_docker_daemon()
    registered_event = CustomerRegistered(
        customer_id=uuid4(),
        name="Jane Doe",
        email="jane@example.com",
        role="customer",
        registered_at=datetime(2026, 4, 21, tzinfo=UTC),
    )
    updated_event = CustomerInfoUpdated(
        customer_id=uuid4(),
        updated_fields=["name", "phone"],
    )

    # Act
    with RabbitMqContainer("rabbitmq:3.13-alpine") as rabbitmq:
        consumer_connection = pika.BlockingConnection(rabbitmq.get_connection_params())
        publisher = RabbitMQEventPublisher(
            connection_factory=lambda: pika.BlockingConnection(
                rabbitmq.get_connection_params()
            ),
            exchange_name="customer.events",
        )
        consumer_channel = consumer_connection.channel()
        consumer_channel.exchange_declare(
            exchange="customer.events",
            exchange_type="topic",
            durable=True,
        )
        queue_name = consumer_channel.queue_declare(
            queue="", exclusive=True
        ).method.queue
        consumer_channel.queue_bind(
            exchange="customer.events",
            queue=queue_name,
            routing_key="CustomerRegistered",
        )
        consumer_channel.queue_bind(
            exchange="customer.events",
            queue=queue_name,
            routing_key="CustomerInfoUpdated",
        )

        publisher.publish(registered_event)
        publisher.publish(updated_event)

        consumed_registered = _wait_for_message(consumer_channel, queue_name)
        consumed_updated = _wait_for_message(consumer_channel, queue_name)

        consumer_connection.close()

    # Assert
    assert consumed_registered["routing_key"] == "CustomerRegistered"
    assert consumed_registered["properties"].content_type == "application/json"
    assert consumed_registered["properties"].type == "CustomerRegistered"
    assert json.loads(consumed_registered["body"]) == {
        "customerId": str(registered_event.customer_id),
        "email": "jane@example.com",
        "eventName": "CustomerRegistered",
        "name": "Jane Doe",
        "registeredAt": "2026-04-21T00:00:00+00:00",
        "role": "customer",
    }
    assert consumed_updated["routing_key"] == "CustomerInfoUpdated"
    assert consumed_updated["properties"].content_type == "application/json"
    assert consumed_updated["properties"].type == "CustomerInfoUpdated"
    assert json.loads(consumed_updated["body"]) == {
        "customerId": str(updated_event.customer_id),
        "eventName": "CustomerInfoUpdated",
        "updatedFields": ["name", "phone"],
    }


def _require_docker_daemon() -> None:
    try:
        import docker

        client = docker.from_env()
        client.ping()
        client.close()
    except Exception as error:  # pragma: no cover - environment guard
        pytest.skip(
            "Docker daemon unavailable; real RabbitMQ integration test requires "
            f"Docker/testcontainers. Original error: {error}"
        )


def _wait_for_message(channel: Any, queue_name: str) -> dict[str, Any]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        method_frame, properties, body = channel.basic_get(
            queue=queue_name, auto_ack=True
        )
        if method_frame is not None:
            return {
                "routing_key": method_frame.routing_key,
                "properties": properties,
                "body": body.decode(),
            }
        time.sleep(0.05)

    pytest.fail("Timed out waiting for RabbitMQ message from real broker")
