from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

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
from internal.interfaces.rest import app as rest_app_module

MYSQL_TEST_URL = (
    "mysql+pymysql://customer:secret@localhost:3306/customer_service?charset=utf8mb4"
)


def test_When_ComposingDatabaseUrlFromMySqlParts_Expect_ResolvedUrlUsesUtf8mb4() -> (
    None
):
    # Arrange
    settings = CustomerServiceSettings(
        database_url=None,
        db_host="mysql",
        db_port=3307,
        db_user="customer_app",
        db_password="super-secret",
        db_name="customer_service",
    )

    # Act
    resolved_url = settings.resolved_database_url

    # Assert
    assert resolved_url == (
        "mysql+pymysql://customer_app:super-secret@mysql:3307/"
        "customer_service?charset=utf8mb4"
    )


def test_When_DatabaseUrlOverrideIsPresent_Expect_ResolvedDatabaseUrlUsesOverride() -> (
    None
):
    # Arrange
    settings = CustomerServiceSettings(
        database_url=MYSQL_TEST_URL,
        db_host="ignored-host",
        db_port=3307,
        db_user="ignored-user",
        db_password="ignored-password",
        db_name="ignored-db",
    )

    # Act
    resolved_url = settings.resolved_database_url

    # Assert
    assert resolved_url == MYSQL_TEST_URL


def test_When_MySqlSettingsAreIncomplete_Expect_ResolvedDatabaseUrlFailsFast() -> None:
    # Arrange
    settings = CustomerServiceSettings(
        database_url=None,
        db_host="mysql",
        db_user="customer_app",
        db_password="super-secret",
        db_name=None,
    )

    # Act / Assert
    with pytest.raises(ValueError, match="Missing MySQL configuration values"):
        _ = settings.resolved_database_url


def test_When_UsingDeploymentMySqlEnvNames_Expect_SettingsResolveDatabaseUrl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.delenv("CUSTOMER_SERVICE_DATABASE_URL", raising=False)
    monkeypatch.setenv("MYSQL_DATABASE", "customer_service")
    monkeypatch.setenv("MYSQL_USER", "customer_app")
    monkeypatch.setenv("MYSQL_PASSWORD", "super-secret")
    monkeypatch.setenv("MYSQL_LOCAL_PORT", "3308")

    # Act
    settings = CustomerServiceSettings()

    # Assert
    assert settings.resolved_database_url == (
        "mysql+pymysql://customer_app:super-secret@localhost:3308/"
        "customer_service?charset=utf8mb4"
    )


def test_When_UsingDeploymentRabbitMqEnvNames_Expect_SettingsResolveRabbitMqUrl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.delenv("CUSTOMER_SERVICE_RABBITMQ_URL", raising=False)
    monkeypatch.setenv("RABBITMQ_HOST", "rabbitmq")
    monkeypatch.setenv("RABBITMQ_DEFAULT_USER", "svc-user")
    monkeypatch.setenv("RABBITMQ_DEFAULT_PASS", "svc-pass")
    monkeypatch.setenv("RABBITMQ_PORT", "5673")

    # Act
    settings = CustomerServiceSettings()

    # Assert
    assert settings.resolved_rabbitmq_url == "amqp://svc-user:svc-pass@rabbitmq:5673/%2F"


def test_When_CustomerServiceRabbitMqUrlIsSet_Expect_ItOverridesDerivedRabbitMqUrl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("RABBITMQ_DEFAULT_USER", "svc-user")
    monkeypatch.setenv("RABBITMQ_DEFAULT_PASS", "svc-pass")
    monkeypatch.setenv("RABBITMQ_PORT", "5673")
    monkeypatch.setenv(
        "CUSTOMER_SERVICE_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F"
    )

    # Act
    settings = CustomerServiceSettings()

    # Assert
    assert settings.resolved_rabbitmq_url == "amqp://guest:guest@localhost:5672/%2F"


def test_When_CreatingAppWithReachableMySql_Expect_StartsAfterConnectionCheck(
    monkeypatch,
) -> None:
    # Arrange
    bind = RecordingEngine()
    session_factory = SimpleNamespace(kw={"bind": bind})
    settings = CustomerServiceSettings(
        database_url=MYSQL_TEST_URL,
        event_publisher_backend="in-memory",
    )

    monkeypatch.setattr(
        rest_app_module,
        "create_session_factory",
        lambda database_url: session_factory,
    )

    # Act
    app = rest_app_module.create_app(settings)

    # Assert
    assert app.state.session_factory is session_factory
    assert bind.connect_calls == 1
    assert not hasattr(rest_app_module, "Base")


def test_When_CreatingAppWithUnreachableMySql_Expect_StartupFailsWithoutRuntimeDdl(
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    session_factory = SimpleNamespace(kw={"bind": FailingEngine()})
    settings = CustomerServiceSettings(
        database_url=MYSQL_TEST_URL,
        event_publisher_backend="in-memory",
    )

    monkeypatch.setattr(
        rest_app_module,
        "create_session_factory",
        lambda database_url: session_factory,
    )

    # Act / Assert
    with pytest.raises(RuntimeError, match="Customer service database is unreachable"):
        rest_app_module.create_app(settings)

    assert not hasattr(rest_app_module, "Base")
    assert "Customer service database connectivity check failed" in caplog.text


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
        database_url=MYSQL_TEST_URL,
        event_publisher_backend="rabbitmq",
        rabbitmq_url="amqp://guest:guest@localhost:5672/%2F",
        rabbitmq_input_queue="customer.validation.requests",
        rabbitmq_request_exchange="customer.exchange",
        rabbitmq_request_routing_key="customer.request",
        rabbitmq_response_exchange="customer.exchange",
        rabbitmq_response_routing_key="customer.response.key",
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
            event_type="BOOKING_Ok",
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
    assert opened_channels[0].published_messages[0]["exchange"] == "customer.exchange"
    assert (
        opened_channels[0].published_messages[0]["routing_key"]
        == "customer.response.key"
    )
    assert opened_channels[1].bindings == [
        {
            "exchange": "customer.exchange",
            "queue": "customer.validation.requests",
            "routing_key": "customer.request",
        }
    ]
    assert opened_channels[0].exchange_declarations == [
        {
            "exchange": "customer.exchange",
            "exchange_type": "direct",
            "durable": True,
        }
    ]
    assert opened_channels[1].exchange_declarations == [
        {
            "exchange": "customer.exchange",
            "exchange_type": "direct",
            "durable": True,
        }
    ]
    assert consumer.input_queue == "customer.validation.requests"
    assert consumer.request_exchange == "customer.exchange"
    assert consumer.request_routing_key == "customer.request"


def test_When_BuildingDedicatedWorkerRuntime_Expect_SeparatedBootstrap(
    monkeypatch,
) -> None:
    # Arrange
    root_dir = Path(__file__).resolve().parents[3]
    (root_dir / "data").mkdir(exist_ok=True)
    settings = CustomerServiceSettings(
        database_url=MYSQL_TEST_URL,
        event_publisher_backend="in-memory",
        rabbitmq_input_queue="customer.validation.requests",
        rabbitmq_request_exchange="customer.exchange",
        rabbitmq_request_routing_key="customer.request",
    )

    # Act
    rest_bind = RecordingEngine()
    rest_session_factory = SimpleNamespace(kw={"bind": rest_bind})
    monkeypatch.setattr(
        rest_app_module,
        "create_session_factory",
        lambda database_url: rest_session_factory,
    )
    monkeypatch.setattr(
        consumer_module,
        "create_session_factory",
        lambda database_url: rest_session_factory,
    )
    monkeypatch.setenv("CUSTOMER_SERVICE_DATABASE_URL", MYSQL_TEST_URL)
    sys.modules.pop("main", None)
    import main

    runtime = build_worker_runtime(settings)

    # Assert
    assert runtime.settings.rabbitmq_input_queue == "customer.validation.requests"
    assert runtime.consumer.input_queue == "customer.validation.requests"
    assert runtime.consumer.request_exchange == "customer.exchange"
    assert runtime.consumer.request_routing_key == "customer.request"
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
        event_type="BookingCreated",
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


def test_When_PublishingValidationResult_Expect_ConfiguredResponseRoutingKeyAndPayloadEventType() -> (
    None
):
    # Arrange
    channel = RecordingChannel()
    publisher = messaging_factory.RabbitMQEventPublisher(
        connection_factory=lambda: RecordingConnection(channel),
        exchange_name="customer.exchange",
        routing_key="customer.response.key",
        properties_factory=lambda event_name: {"type": event_name},
    )
    event = CustomerValidationResult(
        event_id=uuid4(),
        event_type="BOOKING_Ok",
        booking_id=uuid4(),
        customer_id=uuid4(),
        is_valid=False,
        timestamp=datetime(2026, 4, 22, tzinfo=UTC),
    )

    # Act
    publisher.publish(event)

    # Assert
    assert channel.published_messages[0]["exchange"] == "customer.exchange"
    assert channel.published_messages[0]["routing_key"] == "customer.response.key"
    assert json.loads(channel.published_messages[0]["body"]) == {
        "eventId": str(event.event_id),
        "eventType": "BOOKING_Ok",
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
        self.exchange_declarations: list[dict[str, Any]] = []

    def exchange_declare(
        self, *, exchange: str, exchange_type: str, durable: bool
    ) -> None:
        self.exchange_declarations.append(
            {
                "exchange": exchange,
                "exchange_type": exchange_type,
                "durable": durable,
            }
        )

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


class RecordingEngine:
    def __init__(self) -> None:
        self.connect_calls = 0

    def connect(self) -> "RecordingEngineConnection":
        self.connect_calls += 1
        return RecordingEngineConnection()


class RecordingEngineConnection:
    def __enter__(self) -> "RecordingEngineConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class FailingEngine:
    def connect(self) -> "RecordingEngineConnection":
        raise OperationalError("SELECT 1", {}, RuntimeError("unreachable"))


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
        request_exchange="customer.exchange",
        request_routing_key="customer.request",
        input_queue="customer.validation.requests",
        handler=resolved_handler,
        event_publisher=resolved_publisher,
    )
