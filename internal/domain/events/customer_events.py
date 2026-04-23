from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CustomerRegistered:
    customer_id: UUID
    name: str
    email: str
    role: str
    registered_at: datetime
    event_name: str = "CustomerRegistered"


@dataclass(frozen=True, slots=True)
class CustomerInfoUpdated:
    customer_id: UUID
    updated_fields: list[str]
    event_name: str = "CustomerInfoUpdated"


@dataclass(frozen=True, slots=True)
class CustomerDeactivated:
    customer_id: UUID
    deactivated_at: datetime
    reason: str
    event_name: str = "CustomerDeactivated"


@dataclass(frozen=True, slots=True)
class CustomerActivated:
    customer_id: UUID
    activated_at: datetime
    event_name: str = "CustomerActivated"


@dataclass(frozen=True, slots=True)
class CustomerSuspended:
    customer_id: UUID
    suspended_at: datetime
    reason: str
    event_name: str = "CustomerSuspended"


@dataclass(frozen=True, slots=True)
class CustomerSuspensionResolved:
    customer_id: UUID
    resolved_at: datetime
    event_name: str = "CustomerSuspensionResolved"


@dataclass(frozen=True, slots=True)
class CustomerValidationResult:
    event_id: UUID
    booking_id: UUID
    customer_id: UUID
    is_valid: bool
    timestamp: datetime
    event_type: str = "CustomerValidationResult"
