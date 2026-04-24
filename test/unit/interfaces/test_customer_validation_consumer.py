import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from internal.application.dto.customer import ReservationEligibilityDTO
from internal.application.errors import CustomerNotFoundError
from internal.interfaces.messaging.customer_validation_consumer import (
    CustomerValidationConsumer,
)


def test_When_HandlingEligibleBookingCreatedEvent_Expect_AckedValidResult() -> None:
    # Arrange
    inbound_event_id = uuid4()
    customer_id = uuid4()
    booking_id = uuid4()
    use_case = StubValidationUseCase(
        result=ReservationEligibilityDTO(
            customer_id=str(customer_id),
            status="ACTIVE",
            is_eligible=True,
        )
    )
    consumer = CustomerValidationConsumer(use_case)

    # Act
    result = consumer.handle(
        {
            "eventId": str(inbound_event_id),
            "eventType": "BookingCreated",
            "bookingId": str(booking_id),
            "customerId": str(customer_id),
            "timestamp": "2026-04-22T00:00:00+00:00",
            "roomId": str(uuid4()),
            "checkIn": "2026-05-01",
        }
    )

    # Assert
    assert use_case.received_customer_ids == [str(customer_id)]
    assert result.should_ack is True
    assert result.requeue is False
    assert result.event is not None
    assert result.event.event_id != inbound_event_id
    assert isinstance(result.event.event_id, UUID)
    assert result.event.event_type == "BOOKING_Ok"
    assert not hasattr(result.event, "event_name")
    assert result.event.booking_id == booking_id
    assert result.event.customer_id == customer_id
    assert result.event.is_valid is True


def test_When_HandlingIneligibleBookingCreatedEvent_Expect_ResponseUsesBookingCompatibleEventType() -> (
    None
):
    # Arrange
    customer_id = uuid4()
    booking_id = uuid4()
    use_case = StubValidationUseCase(
        result=ReservationEligibilityDTO(
            customer_id=str(customer_id),
            status="INACTIVE",
            is_eligible=False,
        )
    )
    consumer = CustomerValidationConsumer(use_case)

    # Act
    result = consumer.handle(
        {
            "eventId": str(uuid4()),
            "eventType": "BookingCreated",
            "bookingId": str(booking_id),
            "customerId": str(customer_id),
            "timestamp": "2026-04-22T00:00:00+00:00",
        }
    )

    # Assert
    assert result.event is not None
    assert result.event.event_type == "BOOKING_Ok"
    assert result.event.is_valid is False


def test_When_EventTypeUsesBookingExternalValue_Expect_MessageAcceptedAndAcked() -> None:
    # Arrange
    customer_id = uuid4()
    booking_id = uuid4()
    use_case = StubValidationUseCase(
        result=ReservationEligibilityDTO(
            customer_id=str(customer_id),
            status="ACTIVE",
            is_eligible=True,
        )
    )
    consumer = CustomerValidationConsumer(use_case)

    # Act
    result = consumer.handle(
        {
            "eventId": str(uuid4()),
            "eventType": "BOOKING_Ok",
            "bookingId": str(booking_id),
            "customerId": str(customer_id),
            "timestamp": "2026-04-22T00:00:00+00:00",
        }
    )

    # Assert
    assert use_case.received_customer_ids == [str(customer_id)]
    assert result.should_ack is True
    assert result.requeue is False
    assert result.event is not None
    assert result.event.event_type == "BOOKING_Ok"


def test_When_RequestPayloadUsesInvalidUuid_Expect_DiscardedMessage() -> None:
    # Arrange
    use_case = StubValidationUseCase(
        result=ReservationEligibilityDTO(
            customer_id=str(uuid4()),
            status="ACTIVE",
            is_eligible=True,
        )
    )
    consumer = CustomerValidationConsumer(use_case)

    # Act
    result = consumer.handle(
        {
            "eventId": "not-a-uuid",
            "eventType": "BookingCreated",
            "bookingId": str(uuid4()),
            "customerId": str(uuid4()),
            "timestamp": "2026-04-22T00:00:00+00:00",
        }
    )

    # Assert
    assert use_case.received_customer_ids == []
    assert result.should_ack is False
    assert result.requeue is False
    assert result.event is None


def test_When_InvalidBookingId_Expect_DiscardedMessageAndLoggedError(
    caplog,
) -> None:
    # Arrange
    use_case = StubValidationUseCase(
        result=ReservationEligibilityDTO(
            customer_id=str(uuid4()),
            status="ACTIVE",
            is_eligible=True,
        )
    )
    consumer = CustomerValidationConsumer(use_case)
    caplog.set_level(logging.WARNING)

    # Act
    result = consumer.handle(
        {
            "eventId": str(uuid4()),
            "eventType": "BookingCreated",
            "bookingId": "not-a-uuid",
            "customerId": str(uuid4()),
            "timestamp": "2026-04-22T00:00:00+00:00",
        }
    )

    # Assert
    assert use_case.received_customer_ids == []
    assert result.should_ack is False
    assert result.requeue is False
    assert result.event is None
    assert len(caplog.messages) == 1
    assert (
        "Discarding BookingCreated message due to contract validation failure: "
        "bookingId must be a valid UUID payload="
    ) in caplog.messages[0]
    assert "bookingId': 'not-a-uuid'" in caplog.messages[0]


def test_When_RequestPayloadUsesInvalidTimestamp_Expect_DiscardedMessage() -> None:
    # Arrange
    use_case = StubValidationUseCase(
        result=ReservationEligibilityDTO(
            customer_id=str(uuid4()),
            status="ACTIVE",
            is_eligible=True,
        )
    )
    consumer = CustomerValidationConsumer(use_case)

    # Act
    result = consumer.handle(
        {
            "eventId": str(uuid4()),
            "eventType": "BookingCreated",
            "bookingId": str(uuid4()),
            "customerId": str(uuid4()),
            "timestamp": "not-a-timestamp",
        }
    )

    # Assert
    assert use_case.received_customer_ids == []
    assert result.should_ack is False
    assert result.requeue is False
    assert result.event is None


def test_When_EventTypeIsNotBookingCreated_Expect_DiscardedMessage() -> None:
    # Arrange
    use_case = StubValidationUseCase(
        result=ReservationEligibilityDTO(
            customer_id=str(uuid4()),
            status="ACTIVE",
            is_eligible=True,
        )
    )
    consumer = CustomerValidationConsumer(use_case)

    # Act
    result = consumer.handle(
        {
            "eventId": str(uuid4()),
            "eventType": "CustomerValidationRequested",
            "bookingId": str(uuid4()),
            "customerId": str(uuid4()),
            "timestamp": "2026-04-22T00:00:00+00:00",
        }
    )

    # Assert
    assert use_case.received_customer_ids == []
    assert result.should_ack is False
    assert result.requeue is False
    assert result.event is None


def test_When_UnexpectedEventType_Expect_DiscardedMessageAndLoggedError(
    caplog,
) -> None:
    # Arrange
    use_case = StubValidationUseCase(
        result=ReservationEligibilityDTO(
            customer_id=str(uuid4()),
            status="ACTIVE",
            is_eligible=True,
        )
    )
    consumer = CustomerValidationConsumer(use_case)
    caplog.set_level(logging.WARNING)

    # Act
    result = consumer.handle(
        {
            "eventId": str(uuid4()),
            "eventType": "CustomerValidationRequested",
            "bookingId": str(uuid4()),
            "customerId": str(uuid4()),
            "timestamp": "2026-04-22T00:00:00+00:00",
        }
    )

    # Assert
    assert use_case.received_customer_ids == []
    assert result.should_ack is False
    assert result.requeue is False
    assert result.event is None
    assert len(caplog.messages) == 1
    assert (
        "Discarding BookingCreated message due to contract validation failure: "
        "Unsupported event type: CustomerValidationRequested payload="
    ) in caplog.messages[0]
    assert "eventType': 'CustomerValidationRequested'" in caplog.messages[0]


def test_When_CustomerDoesNotExist_Expect_AckedInvalidResult() -> None:
    # Arrange
    customer_id = uuid4()
    booking_id = uuid4()
    use_case = StubValidationUseCase(
        error=CustomerNotFoundError(f"Customer {customer_id} was not found")
    )
    consumer = CustomerValidationConsumer(use_case)

    # Act
    result = consumer.handle(
        {
            "eventId": str(uuid4()),
            "eventType": "BookingCreated",
            "bookingId": str(booking_id),
            "customerId": str(customer_id),
            "timestamp": "2026-04-22T00:00:00+00:00",
        }
    )

    # Assert
    assert use_case.received_customer_ids == [str(customer_id)]
    assert result.should_ack is True
    assert result.requeue is False
    assert result.event is not None
    assert result.event.customer_id == customer_id
    assert result.event.booking_id == booking_id
    assert result.event.is_valid is False


def test_When_CustomerExistsButIsIneligible_Expect_AckedInvalidResult() -> None:
    # Arrange
    customer_id = uuid4()
    booking_id = uuid4()
    use_case = StubValidationUseCase(
        result=ReservationEligibilityDTO(
            customer_id=str(customer_id),
            status="INACTIVE",
            is_eligible=False,
        )
    )
    consumer = CustomerValidationConsumer(use_case)

    # Act
    result = consumer.handle(
        {
            "eventId": str(uuid4()),
            "eventType": "BookingCreated",
            "bookingId": str(booking_id),
            "customerId": str(customer_id),
            "timestamp": "2026-04-22T00:00:00+00:00",
        }
    )

    # Assert
    assert use_case.received_customer_ids == [str(customer_id)]
    assert result.should_ack is True
    assert result.requeue is False
    assert result.event is not None
    assert result.event.customer_id == customer_id
    assert result.event.booking_id == booking_id
    assert result.event.is_valid is False


def test_When_UseCaseRaisesUnexpectedError_Expect_RetryableNack() -> None:
    # Arrange
    customer_id = uuid4()
    use_case = StubValidationUseCase(error=RuntimeError("broker outage"))
    consumer = CustomerValidationConsumer(use_case)

    # Act
    result = consumer.handle(
        {
            "eventId": str(uuid4()),
            "eventType": "BookingCreated",
            "bookingId": str(uuid4()),
            "customerId": str(customer_id),
            "timestamp": "2026-04-22T00:00:00+00:00",
        }
    )

    # Assert
    assert use_case.received_customer_ids == [str(customer_id)]
    assert result.should_ack is False
    assert result.requeue is True
    assert result.event is None


@dataclass
class StubValidationUseCase:
    result: ReservationEligibilityDTO | None = None
    error: Exception | None = None

    def __post_init__(self) -> None:
        self.received_customer_ids: list[str] = []

    def execute(self, customer_id: str) -> ReservationEligibilityDTO:
        self.received_customer_ids.append(customer_id)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result
