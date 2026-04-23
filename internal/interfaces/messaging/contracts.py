from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BookingCreatedMessage:
    event_id: UUID
    event_type: str
    booking_id: UUID
    customer_id: UUID
    timestamp: datetime

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "BookingCreatedMessage":
        event_id = _require_uuid(payload, "eventId")
        event_type = _require_non_empty_string(payload, "eventType")
        booking_id = _require_uuid(payload, "bookingId")
        customer_id = _require_uuid(payload, "customerId")
        timestamp = _require_datetime(payload, "timestamp")
        return cls(
            event_id=event_id,
            event_type=event_type,
            booking_id=booking_id,
            customer_id=customer_id,
            timestamp=timestamp,
        )


def _require_non_empty_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value


def _require_uuid(payload: dict[str, object], key: str) -> UUID:
    value = _require_non_empty_string(payload, key)
    try:
        return UUID(value)
    except ValueError as error:
        raise ValueError(f"{key} must be a valid UUID") from error


def _require_datetime(payload: dict[str, object], key: str) -> datetime:
    value = _require_non_empty_string(payload, key)
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{key} must be a valid ISO-8601 datetime") from error
