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
        try:
            message = BookingCreatedMessage.from_payload(payload)
            self._validate_event_type(message.event_type)
        except ValueError as error:
            logger.warning(
                (
                    "Discarding BookingCreated message due to contract "
                    "validation failure: %s"
                ),
                error,
            )
            return CustomerValidationHandlingResult(should_ack=False, requeue=False)

        try:
            result = self._use_case.execute(str(message.customer_id))
        except CustomerNotFoundError:
            return CustomerValidationHandlingResult(
                should_ack=True,
                requeue=False,
                event=self._build_result_event(message=message, is_valid=False),
            )
        except Exception:
            return CustomerValidationHandlingResult(should_ack=False, requeue=True)

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
