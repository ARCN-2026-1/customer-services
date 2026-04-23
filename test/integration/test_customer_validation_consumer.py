import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pika
import pytest
from testcontainers.rabbitmq import RabbitMqContainer

from internal.application.usecases.validate_customer_for_reservation import (
    ValidateCustomerForReservation,
)
from internal.domain.entities.customer import Customer
from internal.domain.valueobjects.customer_role import CustomerRole
from internal.domain.valueobjects.customer_status import CustomerStatus
from internal.domain.valueobjects.email import Email
from internal.infrastructure.config.settings import CustomerServiceSettings
from internal.infrastructure.messaging.factory import (
    create_customer_validation_consumer,
)
from internal.infrastructure.messaging.rabbitmq_event_publisher import (
    RabbitMQEventPublisher,
)
from internal.infrastructure.persistence.models import Base
from internal.infrastructure.persistence.sqlalchemy_customer_repository import (
    SqlAlchemyCustomerRepository,
)
from internal.infrastructure.persistence.unit_of_work import create_session_factory
from internal.interfaces.messaging.customer_validation_consumer import (
    CustomerValidationConsumer,
)


def test_When_ConsumingEligibleBookingCreatedEvent_Expect_ResultPublished() -> None:
    # Arrange
    _require_docker_daemon()
    customer_id = uuid4()
    booking_id = uuid4()
    repository = _build_repository(
        customers=[
            Customer(
                customer_id=customer_id,
                name="Jane Doe",
                email=Email("jane@example.com"),
                phone="+57-3000000000",
                password_hash="hashed::plain-password",
                status=CustomerStatus.ACTIVE,
                role=CustomerRole.CUSTOMER,
                registered_at=datetime(2026, 4, 21, tzinfo=UTC),
            )
        ]
    )

    # Act
    with RabbitMqContainer("rabbitmq:3.13-alpine") as rabbitmq:
        connection_params = rabbitmq.get_connection_params()
        rabbitmq_url = (
            "amqp://"
            f"{connection_params.credentials.username}:"
            f"{connection_params.credentials.password}@"
            f"{connection_params.host}:{connection_params.port}/%2F"
        )
        settings = CustomerServiceSettings(
            database_url="sqlite://",
            event_publisher_backend="rabbitmq",
            rabbitmq_url=rabbitmq_url,
            rabbitmq_exchange="customer.events",
            rabbitmq_input_queue="customer.validation.requests",
            rabbitmq_consumer_exchange="booking.events",
        )
        observer_connection = pika.BlockingConnection(connection_params)
        observer_channel = observer_connection.channel()
        observer_channel.exchange_declare(
            exchange="customer.events",
            exchange_type="topic",
            durable=True,
        )
        response_queue = observer_channel.queue_declare(
            queue="", exclusive=True
        ).method.queue
        observer_channel.queue_bind(
            exchange="customer.events",
            queue=response_queue,
            routing_key="CustomerValidationResult",
        )

        worker = create_customer_validation_consumer(
            settings=settings,
            handler=CustomerValidationConsumer(
                ValidateCustomerForReservation(repository)
            ),
            event_publisher=RabbitMQEventPublisher(
                connection_factory=lambda: pika.BlockingConnection(connection_params),
                exchange_name="customer.events",
            ),
        )
        worker.ensure_topology()
        observer_channel.basic_publish(
            exchange="booking.events",
            routing_key="BookingCreated",
            body=json.dumps(
                {
                    "eventId": str(uuid4()),
                    "eventType": "BookingCreated",
                    "bookingId": str(booking_id),
                    "customerId": str(customer_id),
                    "timestamp": "2026-04-22T00:00:00+00:00",
                    "totalPrice": 125.50,
                }
            ),
            properties=pika.BasicProperties(content_type="application/json"),
        )

        processed = worker.process_next_message()
        published_message = _wait_for_message(observer_channel, response_queue)
        observer_connection.close()

    # Assert
    assert processed is True
    assert published_message["routing_key"] == "CustomerValidationResult"
    published_payload = json.loads(published_message["body"])
    assert UUID(published_payload["eventId"])
    assert published_payload["eventType"] == "CustomerValidationResult"
    assert published_payload["bookingId"] == str(booking_id)
    assert published_payload["customerId"] == str(customer_id)
    assert published_payload["isValid"] is True
    assert "eventName" not in published_payload
    assert "totalPrice" not in published_payload
    assert datetime.fromisoformat(published_payload["timestamp"]).tzinfo is not None


def test_When_ValidatedCustomerIsMissing_Expect_InvalidResultPublished() -> None:
    # Arrange
    _require_docker_daemon()
    booking_id = uuid4()
    customer_id = uuid4()
    repository = _build_repository()

    # Act
    with RabbitMqContainer("rabbitmq:3.13-alpine") as rabbitmq:
        connection_params = rabbitmq.get_connection_params()
        rabbitmq_url = (
            "amqp://"
            f"{connection_params.credentials.username}:"
            f"{connection_params.credentials.password}@"
            f"{connection_params.host}:{connection_params.port}/%2F"
        )
        settings = CustomerServiceSettings(
            database_url="sqlite://",
            event_publisher_backend="rabbitmq",
            rabbitmq_url=rabbitmq_url,
            rabbitmq_exchange="customer.events",
            rabbitmq_input_queue="customer.validation.requests",
            rabbitmq_consumer_exchange="booking.events",
        )
        observer_connection = pika.BlockingConnection(connection_params)
        observer_channel = observer_connection.channel()
        observer_channel.exchange_declare(
            exchange="customer.events",
            exchange_type="topic",
            durable=True,
        )
        response_queue = observer_channel.queue_declare(
            queue="", exclusive=True
        ).method.queue
        observer_channel.queue_bind(
            exchange="customer.events",
            queue=response_queue,
            routing_key="CustomerValidationResult",
        )

        worker = create_customer_validation_consumer(
            settings=settings,
            handler=CustomerValidationConsumer(
                ValidateCustomerForReservation(repository)
            ),
            event_publisher=RabbitMQEventPublisher(
                connection_factory=lambda: pika.BlockingConnection(connection_params),
                exchange_name="customer.events",
            ),
        )
        worker.ensure_topology()
        observer_channel.basic_publish(
            exchange="booking.events",
            routing_key="BookingCreated",
            body=json.dumps(
                {
                    "eventId": str(uuid4()),
                    "eventType": "BookingCreated",
                    "bookingId": str(booking_id),
                    "customerId": str(customer_id),
                    "timestamp": "2026-04-22T00:00:00+00:00",
                }
            ),
            properties=pika.BasicProperties(content_type="application/json"),
        )

        processed = worker.process_next_message()
        published_message = _wait_for_message(observer_channel, response_queue)
        request_message = observer_channel.basic_get(
            queue="customer.validation.requests", auto_ack=True
        )
        observer_connection.close()

    # Assert
    assert processed is True
    assert request_message[0] is None
    published_payload = json.loads(published_message["body"])
    assert published_payload["isValid"] is False
    assert published_payload["bookingId"] == str(booking_id)
    assert published_payload["customerId"] == str(customer_id)


def test_When_ExistingCustomerIsInactive_Expect_InvalidResultPublished() -> None:
    # Arrange
    _require_docker_daemon()
    booking_id = uuid4()
    customer_id = uuid4()
    repository = _build_repository(
        customers=[
            Customer(
                customer_id=customer_id,
                name="Inactive Jane",
                email=Email("inactive.jane@example.com"),
                phone="+57-3000001111",
                password_hash="hashed::plain-password",
                status=CustomerStatus.INACTIVE,
                role=CustomerRole.CUSTOMER,
                registered_at=datetime(2026, 4, 21, tzinfo=UTC),
            )
        ]
    )

    # Act
    with RabbitMqContainer("rabbitmq:3.13-alpine") as rabbitmq:
        connection_params = rabbitmq.get_connection_params()
        rabbitmq_url = (
            "amqp://"
            f"{connection_params.credentials.username}:"
            f"{connection_params.credentials.password}@"
            f"{connection_params.host}:{connection_params.port}/%2F"
        )
        settings = CustomerServiceSettings(
            database_url="sqlite://",
            event_publisher_backend="rabbitmq",
            rabbitmq_url=rabbitmq_url,
            rabbitmq_exchange="customer.events",
            rabbitmq_input_queue="customer.validation.requests",
            rabbitmq_consumer_exchange="booking.events",
        )
        observer_connection = pika.BlockingConnection(connection_params)
        observer_channel = observer_connection.channel()
        observer_channel.exchange_declare(
            exchange="customer.events",
            exchange_type="topic",
            durable=True,
        )
        response_queue = observer_channel.queue_declare(
            queue="", exclusive=True
        ).method.queue
        observer_channel.queue_bind(
            exchange="customer.events",
            queue=response_queue,
            routing_key="CustomerValidationResult",
        )

        worker = create_customer_validation_consumer(
            settings=settings,
            handler=CustomerValidationConsumer(
                ValidateCustomerForReservation(repository)
            ),
            event_publisher=RabbitMQEventPublisher(
                connection_factory=lambda: pika.BlockingConnection(connection_params),
                exchange_name="customer.events",
            ),
        )
        worker.ensure_topology()
        observer_channel.basic_publish(
            exchange="booking.events",
            routing_key="BookingCreated",
            body=json.dumps(
                {
                    "eventId": str(uuid4()),
                    "eventType": "BookingCreated",
                    "bookingId": str(booking_id),
                    "customerId": str(customer_id),
                    "timestamp": "2026-04-22T00:00:00+00:00",
                }
            ),
            properties=pika.BasicProperties(content_type="application/json"),
        )

        processed = worker.process_next_message()
        published_message = _wait_for_message(observer_channel, response_queue)
        request_message = observer_channel.basic_get(
            queue="customer.validation.requests", auto_ack=True
        )
        observer_connection.close()

    # Assert
    assert processed is True
    assert request_message[0] is None
    published_payload = json.loads(published_message["body"])
    assert UUID(published_payload["eventId"])
    assert published_payload["customerId"] == str(customer_id)
    assert published_payload["bookingId"] == str(booking_id)
    assert published_payload["isValid"] is False
    assert "eventName" not in published_payload


def test_When_RequestPayloadIsMalformed_Expect_DiscardedWithoutPublishing() -> None:
    # Arrange
    _require_docker_daemon()

    # Act
    with RabbitMqContainer("rabbitmq:3.13-alpine") as rabbitmq:
        connection_params = rabbitmq.get_connection_params()
        rabbitmq_url = (
            "amqp://"
            f"{connection_params.credentials.username}:"
            f"{connection_params.credentials.password}@"
            f"{connection_params.host}:{connection_params.port}/%2F"
        )
        settings = CustomerServiceSettings(
            database_url="sqlite://",
            event_publisher_backend="rabbitmq",
            rabbitmq_url=rabbitmq_url,
            rabbitmq_exchange="customer.events",
            rabbitmq_input_queue="customer.validation.requests",
            rabbitmq_consumer_exchange="booking.events",
        )
        observer_connection = pika.BlockingConnection(connection_params)
        observer_channel = observer_connection.channel()
        observer_channel.exchange_declare(
            exchange="customer.events",
            exchange_type="topic",
            durable=True,
        )
        response_queue = observer_channel.queue_declare(
            queue="", exclusive=True
        ).method.queue
        observer_channel.queue_bind(
            exchange="customer.events",
            queue=response_queue,
            routing_key="CustomerValidationResult",
        )

        worker = create_customer_validation_consumer(
            settings=settings,
            handler=CustomerValidationConsumer(
                ValidateCustomerForReservation(_build_repository())
            ),
            event_publisher=RabbitMQEventPublisher(
                connection_factory=lambda: pika.BlockingConnection(connection_params),
                exchange_name="customer.events",
            ),
        )
        worker.ensure_topology()
        observer_channel.basic_publish(
            exchange="booking.events",
            routing_key="BookingCreated",
            body=json.dumps(
                {
                    "eventType": "BookingCreated",
                    "bookingId": str(uuid4()),
                    "timestamp": "2026-04-22T00:00:00+00:00",
                }
            ),
            properties=pika.BasicProperties(content_type="application/json"),
        )

        processed = worker.process_next_message()
        time.sleep(0.2)
        discarded_message = observer_channel.basic_get(
            queue="customer.validation.requests", auto_ack=True
        )
        outbound_message = observer_channel.basic_get(
            queue=response_queue, auto_ack=True
        )
        observer_connection.close()

    # Assert
    assert processed is True
    assert discarded_message[0] is None
    assert outbound_message[0] is None


def test_When_UseCaseFailsUnexpectedly_Expect_MessageRequeued() -> None:
    # Arrange
    _require_docker_daemon()
    customer_id = uuid4()

    # Act
    with RabbitMqContainer("rabbitmq:3.13-alpine") as rabbitmq:
        connection_params = rabbitmq.get_connection_params()
        rabbitmq_url = (
            "amqp://"
            f"{connection_params.credentials.username}:"
            f"{connection_params.credentials.password}@"
            f"{connection_params.host}:{connection_params.port}/%2F"
        )
        settings = CustomerServiceSettings(
            database_url="sqlite://",
            event_publisher_backend="rabbitmq",
            rabbitmq_url=rabbitmq_url,
            rabbitmq_exchange="customer.events",
            rabbitmq_input_queue="customer.validation.requests",
            rabbitmq_consumer_exchange="booking.events",
        )
        observer_connection = pika.BlockingConnection(connection_params)
        observer_channel = observer_connection.channel()

        worker = create_customer_validation_consumer(
            settings=settings,
            handler=CustomerValidationConsumer(ExplodingValidationUseCase()),
            event_publisher=RabbitMQEventPublisher(
                connection_factory=lambda: pika.BlockingConnection(connection_params),
                exchange_name="customer.events",
            ),
        )
        worker.ensure_topology()
        observer_channel.basic_publish(
            exchange="booking.events",
            routing_key="BookingCreated",
            body=json.dumps(
                {
                    "eventId": str(uuid4()),
                    "eventType": "BookingCreated",
                    "bookingId": str(uuid4()),
                    "customerId": str(customer_id),
                    "timestamp": "2026-04-22T00:00:00+00:00",
                }
            ),
            properties=pika.BasicProperties(content_type="application/json"),
        )

        processed = worker.process_next_message()
        requeued_message = _wait_for_requeued_message(
            observer_channel, "customer.validation.requests"
        )
        observer_connection.close()

    # Assert
    assert processed is True
    requeued_payload = json.loads(requeued_message)
    assert UUID(requeued_payload["eventId"])
    assert requeued_payload["eventType"] == "BookingCreated"


class ExplodingValidationUseCase:
    def execute(self, customer_id: str) -> Any:
        raise RuntimeError(f"database offline for {customer_id}")


def _build_repository(
    *, customers: list[Customer] | None = None
) -> SqlAlchemyCustomerRepository:
    session_factory = create_session_factory("sqlite://")
    Base.metadata.create_all(bind=session_factory.kw["bind"])
    repository = SqlAlchemyCustomerRepository(session_factory)

    for customer in customers or []:
        repository.add(customer)

    return repository


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

    pytest.fail("Timed out waiting for customer validation result event")


def _wait_for_requeued_message(channel: Any, queue_name: str) -> str:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        method_frame, _, body = channel.basic_get(queue=queue_name, auto_ack=True)
        if method_frame is not None:
            return body.decode()
        time.sleep(0.05)

    pytest.fail("Timed out waiting for requeued validation request")
