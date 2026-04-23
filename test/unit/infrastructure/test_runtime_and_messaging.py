from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import consumer as consumer_module
from consumer import build_worker_runtime
from internal.application.dto.customer import ReservationEligibilityDTO
from internal.application.errors import EventPublicationError
from internal.domain.events.customer_events import CustomerValidationResult
from internal.infrastructure.config.settings import CustomerServiceSettings
from internal.infrastructure.messaging import factory as messaging_factory
from internal.infrastructure.messaging.factory import (
    create_customer_validation_consumer,
    create_event_publisher,
)
from internal.infrastructure.messaging.rabbitmq_customer_validation_consumer import (
    RabbitMQCustomerValidationConsumer,
)
from internal.interfaces.messaging.customer_validation_consumer import (
    CustomerValidationConsumer,
    CustomerValidationHandlingResult,
)


def test_When_StartingWorkerProcess_Expect_TopologyPreparedBeforeConsumption(
    monkeypatch,
) -> None:
    # Arrange
    runtime_consumer = SpyRuntimeConsumer()
    monkeypatch.setattr(
        consumer_module,
        "build_worker_runtime",
        lambda: SimpleNamespace(consumer=runtime_consumer),
    )

    # Act
    consumer_module.main()

    # Assert
    assert runtime_consumer.calls == ["ensure_topology", "start_consuming"]


def test_When_CreatingRabbitMqPublisherAndConsumer_Expect_SharedRabbitMqConfiguration(
    monkeypatch,
) -> None:
    # Arrange
    connection_calls: list[tuple[str, int, int]] = []
    opened_channels: list[RecordingChannel] = []
    settings = CustomerServiceSettings(
        database_url="sqlite://",
        event_publisher_backend="rabbitmq",
        rabbitmq_url="amqp://guest:guest@localhost:5672/%2F",
        rabbitmq_input_queue="customer.validation.requests",
        rabbitmq_consumer_exchange="booking.events",
        rabbitmq_exchange="customer.events",
    )
    handler = CustomerValidationConsumer(StubValidationUseCase())

    def fake_open_rabbitmq_connection(
        url: str,
        *,
        heartbeat: int,
        blocked_connection_timeout: int,
    ) -> RecordingConnection:
        connection_calls.append((url, heartbeat, blocked_connection_timeout))
        channel = RecordingChannel()
        opened_channels.append(channel)
        return RecordingConnection(channel)

    monkeypatch.setattr(
        messaging_factory,
        "open_rabbitmq_connection",
        fake_open_rabbitmq_connection,
    )

    # Act
    publisher = create_event_publisher(settings)
    consumer = create_customer_validation_consumer(
        settings=settings,
        handler=handler,
        event_publisher=publisher,
    )
    publisher.publish(
        CustomerValidationResult(
            event_id=uuid4(),
            booking_id=uuid4(),
            customer_id=uuid4(),
            is_valid=True,
            timestamp=datetime(2026, 4, 22, tzinfo=UTC),
        )
    )
    consumer.ensure_topology()

    # Assert
    assert connection_calls == [
        ("amqp://guest:guest@localhost:5672/%2F", 60, 30),
        ("amqp://guest:guest@localhost:5672/%2F", 60, 30),
    ]
    assert opened_channels[0].published_messages[0]["exchange"] == "customer.events"
    assert (
        opened_channels[0].published_messages[0]["routing_key"]
        == "CustomerValidationResult"
    )
    assert opened_channels[1].bindings == [
        {
            "exchange": "booking.events",
            "queue": "customer.validation.requests",
            "routing_key": "BookingCreated",
        }
    ]
    assert consumer.input_queue == "customer.validation.requests"
    assert consumer.consumer_exchange == "booking.events"


def test_When_BuildingDedicatedWorkerRuntime_Expect_SeparatedBootstrap() -> None:
    # Arrange
    root_dir = Path(__file__).resolve().parents[3]
    (root_dir / "data").mkdir(exist_ok=True)
    settings = CustomerServiceSettings(
        database_url="sqlite://",
        event_publisher_backend="in-memory",
        rabbitmq_input_queue="customer.validation.requests",
        rabbitmq_consumer_exchange="booking.events",
    )

    # Act
    import main

    runtime = build_worker_runtime(settings)

    # Assert
    assert runtime.settings.rabbitmq_input_queue == "customer.validation.requests"
    assert runtime.consumer.input_queue == "customer.validation.requests"
    assert runtime.consumer.consumer_exchange == "booking.events"
    assert runtime.handler is not None
    assert hasattr(main, "app")
    assert not hasattr(main.app.state, "customer_validation_consumer")


def test_When_NoMessageIsAvailable_Expect_ConsumerReturnsFalse() -> None:
    # Arrange
    channel = RecordingChannel(message=(None, None, None))
    consumer = _build_rabbitmq_consumer(channel=channel)

    # Act
    processed = consumer.process_next_message()

    # Assert
    assert processed is False
    assert channel.acked_delivery_tags == []
    assert channel.nacked_messages == []


def test_When_RequestPayloadIsNotAnObject_Expect_MessageDiscarded() -> None:
    # Arrange
    channel = RecordingChannel(
        message=(
            DeliveryFrame(delivery_tag=7),
            None,
            json.dumps(["not", "a", "mapping"]).encode(),
        )
    )
    consumer = _build_rabbitmq_consumer(channel=channel)

    # Act
    processed = consumer.process_next_message()

    # Assert
    assert processed is True
    assert channel.acked_delivery_tags == []
    assert channel.nacked_messages == [{"delivery_tag": 7, "requeue": False}]


def test_When_PublishingResultFails_Expect_MessageRequeued() -> None:
    # Arrange
    event = CustomerValidationResult(
        event_id=uuid4(),
        booking_id=uuid4(),
        customer_id=uuid4(),
        is_valid=True,
        timestamp=datetime(2026, 4, 22, tzinfo=UTC),
    )
    channel = RecordingChannel(
        message=(
            DeliveryFrame(delivery_tag=9),
            None,
            json.dumps(
                {
                    "eventId": str(event.event_id),
                    "eventType": "BookingCreated",
                    "bookingId": str(event.booking_id),
                    "customerId": str(event.customer_id),
                    "timestamp": "2026-04-22T00:00:00+00:00",
                }
            ).encode(),
        )
    )
    handler = StubHandler(
        result=CustomerValidationHandlingResult(
            should_ack=True,
            requeue=False,
            event=event,
        )
    )
    publisher = FailingPublisher()
    consumer = _build_rabbitmq_consumer(
        channel=channel,
        handler=handler,
        publisher=publisher,
    )

    # Act
    processed = consumer.process_next_message()

    # Assert
    assert processed is True
    assert handler.received_payloads == [
        {
            "eventId": str(event.event_id),
            "eventType": "BookingCreated",
            "bookingId": str(event.booking_id),
            "customerId": str(event.customer_id),
            "timestamp": "2026-04-22T00:00:00+00:00",
        }
    ]
    assert publisher.published_events == [event]
    assert channel.acked_delivery_tags == []
    assert channel.nacked_messages == [{"delivery_tag": 9, "requeue": True}]


def test_When_StartingAdapterConsumption_Expect_PollingUntilQueueDrained() -> None:
    # Arrange
    consumer = _build_rabbitmq_consumer(channel=RecordingChannel())
    calls: list[str] = []
    results = iter([True, True, False])

    def fake_process_next_message() -> bool:
        calls.append("processed")
        return next(results)

    consumer.process_next_message = fake_process_next_message  # type: ignore[method-assign]

    # Act
    consumer.start_consuming()

    # Assert
    assert calls == ["processed", "processed", "processed"]


def test_When_PublishingValidationResult_Expect_EventTypeRoutingKey() -> None:
    # Arrange
    channel = RecordingChannel()
    publisher = messaging_factory.RabbitMQEventPublisher(
        connection_factory=lambda: RecordingConnection(channel),
        exchange_name="customer.events",
        properties_factory=lambda event_name: {"type": event_name},
    )
    event = CustomerValidationResult(
        event_id=uuid4(),
        booking_id=uuid4(),
        customer_id=uuid4(),
        is_valid=False,
        timestamp=datetime(2026, 4, 22, tzinfo=UTC),
    )

    # Act
    publisher.publish(event)

    # Assert
    assert channel.published_messages[0]["routing_key"] == "CustomerValidationResult"
    assert json.loads(channel.published_messages[0]["body"]) == {
        "eventId": str(event.event_id),
        "eventType": "CustomerValidationResult",
        "bookingId": str(event.booking_id),
        "customerId": str(event.customer_id),
        "isValid": False,
        "timestamp": event.timestamp.isoformat(),
    }
    assert "eventName" not in channel.published_messages[0]["body"]


def test_When_PublishingLegacyLifecycleEvent_Expect_EventNameRoutingKey() -> None:
    # Arrange
    channel = RecordingChannel()
    publisher = messaging_factory.RabbitMQEventPublisher(
        connection_factory=lambda: RecordingConnection(channel),
        exchange_name="customer.events",
        properties_factory=lambda event_name: {"type": event_name},
    )
    event = LegacyLifecycleEvent(customer_id=uuid4())

    # Act
    publisher.publish(event)

    # Assert
    assert channel.published_messages[0]["routing_key"] == "CustomerRegistered"
    assert json.loads(channel.published_messages[0]["body"]) == {
        "customerId": str(event.customer_id),
        "eventName": "CustomerRegistered",
    }


class StubValidationUseCase:
    def execute(self, customer_id: str) -> ReservationEligibilityDTO:
        return ReservationEligibilityDTO(
            customer_id=customer_id,
            status="ACTIVE",
            is_eligible=True,
        )


class SpyRuntimeConsumer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def ensure_topology(self) -> None:
        self.calls.append("ensure_topology")

    def start_consuming(self) -> None:
        self.calls.append("start_consuming")


@dataclass
class DeliveryFrame:
    delivery_tag: int


class RecordingChannel:
    def __init__(
        self, message: tuple[Any, Any, bytes] | tuple[None, None, None] | None = None
    ) -> None:
        self._message = message or (None, None, None)
        self.acked_delivery_tags: list[int] = []
        self.nacked_messages: list[dict[str, Any]] = []
        self.published_messages: list[dict[str, Any]] = []
        self.bindings: list[dict[str, Any]] = []

    def exchange_declare(
        self, *, exchange: str, exchange_type: str, durable: bool
    ) -> None:
        return None

    def queue_declare(self, *, queue: str, durable: bool) -> None:
        return None

    def queue_bind(self, *, exchange: str, queue: str, routing_key: str) -> None:
        self.bindings.append(
            {
                "exchange": exchange,
                "queue": queue,
                "routing_key": routing_key,
            }
        )

    def basic_publish(
        self,
        *,
        exchange: str,
        routing_key: str,
        body: str,
        properties: Any,
    ) -> None:
        self.published_messages.append(
            {
                "exchange": exchange,
                "routing_key": routing_key,
                "body": body,
                "properties": properties,
            }
        )

    def basic_get(self, *, queue: str, auto_ack: bool) -> tuple[Any, Any, Any]:
        return self._message

    def basic_ack(self, delivery_tag: int) -> None:
        self.acked_delivery_tags.append(delivery_tag)

    def basic_nack(self, delivery_tag: int, requeue: bool) -> None:
        self.nacked_messages.append({"delivery_tag": delivery_tag, "requeue": requeue})


class RecordingConnection:
    def __init__(self, channel: RecordingChannel) -> None:
        self._channel = channel
        self.closed = False

    def channel(self) -> RecordingChannel:
        return self._channel

    def close(self) -> None:
        self.closed = True


@dataclass
class StubHandler:
    result: CustomerValidationHandlingResult

    def __post_init__(self) -> None:
        self.received_payloads: list[dict[str, Any]] = []

    def handle(self, payload: dict[str, Any]) -> CustomerValidationHandlingResult:
        self.received_payloads.append(payload)
        return self.result


class FailingPublisher:
    def __init__(self) -> None:
        self.published_events: list[object] = []

    def publish(self, event: object) -> None:
        self.published_events.append(event)
        raise EventPublicationError("publisher unavailable")


@dataclass(frozen=True)
class LegacyLifecycleEvent:
    customer_id: Any
    event_name: str = "CustomerRegistered"


def _build_rabbitmq_consumer(
    *,
    channel: RecordingChannel,
    handler: Any | None = None,
    publisher: Any | None = None,
) -> RabbitMQCustomerValidationConsumer:
    resolved_handler = handler or StubHandler(
        result=CustomerValidationHandlingResult(
            should_ack=True,
            requeue=False,
            event=None,
        )
    )
    resolved_publisher = publisher or create_event_publisher(
        CustomerServiceSettings(event_publisher_backend="in-memory")
    )
    return RabbitMQCustomerValidationConsumer(
        connection_factory=lambda: RecordingConnection(channel),
        consumer_exchange="booking.events",
        input_queue="customer.validation.requests",
        handler=resolved_handler,
        event_publisher=resolved_publisher,
    )
