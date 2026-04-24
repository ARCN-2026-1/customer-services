from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from internal.application.dto.customer import ReservationEligibilityDTO
from internal.application.errors import CustomerNotFoundError
from internal.domain.events.customer_events import CustomerValidationResult
from internal.interfaces.messaging.contracts import BookingCreatedMessage

ACCEPTED_EVENT_TYPES = frozenset({"BookingCreated", "BOOKING_Ok"})
RESPONSE_EVENT_TYPE = "BOOKING_Ok"
logger = logging.getLogger(__name__)


class ReservationValidationUseCase(Protocol):
    def execute(self, customer_id: str) -> ReservationEligibilityDTO: ...


@dataclass(frozen=True, slots=True)
class CustomerValidationHandlingResult:
    should_ack: bool
    requeue: bool
    event: CustomerValidationResult | None = None


class CustomerValidationConsumer:
    def __init__(self, use_case: ReservationValidationUseCase) -> None:
        self._use_case = use_case

    def handle(self, payload: dict[str, object]) -> CustomerValidationHandlingResult:
        payload_snapshot = _build_payload_snapshot(payload)
        logger.info(
            "Received customer validation request payload=%s",
            payload_snapshot,
        )
        try:
            message = BookingCreatedMessage.from_payload(payload)
            self._validate_event_type(message.event_type)
        except ValueError as error:
            logger.warning(
                (
                    "Discarding BookingCreated message due to contract validation "
                    "failure: %s payload=%s"
                ),
                error,
                payload_snapshot,
            )
            return CustomerValidationHandlingResult(should_ack=False, requeue=False)

        try:
            result = self._use_case.execute(str(message.customer_id))
        except CustomerNotFoundError:
            logger.info(
                (
                    "Customer validation completed with missing customer "
                    "booking_id=%s customer_id=%s"
                ),
                message.booking_id,
                message.customer_id,
            )
            return CustomerValidationHandlingResult(
                should_ack=True,
                requeue=False,
                event=self._build_result_event(message=message, is_valid=False),
            )
        except Exception:
            logger.exception(
                "Customer validation failed booking_id=%s customer_id=%s",
                message.booking_id,
                message.customer_id,
            )
            return CustomerValidationHandlingResult(should_ack=False, requeue=True)

        logger.info(
            "Customer validation completed booking_id=%s customer_id=%s is_valid=%s",
            message.booking_id,
            message.customer_id,
            result.is_eligible,
        )
        return CustomerValidationHandlingResult(
            should_ack=True,
            requeue=False,
            event=self._build_result_event(
                message=message,
                is_valid=result.is_eligible,
            ),
        )

    def _validate_event_type(self, event_type: str) -> None:
        if event_type not in ACCEPTED_EVENT_TYPES:
            raise ValueError(f"Unsupported event type: {event_type}")

    def _build_result_event(
        self,
        *,
        message: BookingCreatedMessage,
        is_valid: bool,
    ) -> CustomerValidationResult:
        return CustomerValidationResult(
            event_id=uuid4(),
            event_type=RESPONSE_EVENT_TYPE,
            booking_id=message.booking_id,
            customer_id=message.customer_id,
            is_valid=is_valid,
            timestamp=datetime.now(UTC),
        )


def _build_payload_snapshot(payload: dict[str, object]) -> dict[str, object | None]:
    return {
        "eventId": payload.get("eventId"),
        "eventType": payload.get("eventType"),
        "bookingId": payload.get("bookingId"),
        "customerId": payload.get("customerId"),
        "timestamp": payload.get("timestamp"),
    }
