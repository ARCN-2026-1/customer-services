from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from internal.domain.errors import DomainRuleViolation
from internal.domain.events.customer_events import (
    CustomerActivated,
    CustomerDeactivated,
    CustomerInfoUpdated,
    CustomerRegistered,
    CustomerSuspended,
    CustomerSuspensionResolved,
)
from internal.domain.valueobjects.customer_role import CustomerRole
from internal.domain.valueobjects.customer_status import CustomerStatus
from internal.domain.valueobjects.email import Email


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Customer:
    customer_id: UUID
    name: str
    email: Email
    phone: str | None
    password_hash: str
    status: CustomerStatus
    role: CustomerRole
    registered_at: datetime
    _domain_events: list[Any] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Customer name is required")
        if not self.password_hash.strip():
            raise ValueError("Customer password hash is required")

    @classmethod
    def register(
        cls,
        *,
        customer_id: UUID,
        name: str,
        email: Email,
        phone: str | None,
        password_hash: str,
        registered_at: datetime,
        role: CustomerRole = CustomerRole.CUSTOMER,
    ) -> "Customer":
        customer = cls(
            customer_id=customer_id,
            name=name,
            email=email,
            phone=phone,
            password_hash=password_hash,
            status=CustomerStatus.ACTIVE,
            role=role,
            registered_at=registered_at,
        )
        customer._record_event(
            CustomerRegistered(
                customer_id=customer.customer_id,
                name=customer.name,
                email=customer.email.value,
                role=customer.role.value,
                registered_at=customer.registered_at,
            )
        )
        return customer

    @property
    def is_eligible_for_reservation(self) -> bool:
        return self.status is CustomerStatus.ACTIVE

    def deactivate(self, *, reason: str) -> None:
        if self.status is CustomerStatus.SUSPENDED:
            raise DomainRuleViolation("Cannot deactivate a suspended customer")
        if self.status is not CustomerStatus.ACTIVE:
            raise DomainRuleViolation("Cannot deactivate a customer that is not active")

        self.status = CustomerStatus.INACTIVE
        self._record_event(
            CustomerDeactivated(
                customer_id=self.customer_id,
                deactivated_at=_utc_now(),
                reason=reason,
            )
        )

    def activate(self) -> None:
        if self.status is not CustomerStatus.INACTIVE:
            raise DomainRuleViolation("Cannot activate a customer that is not inactive")

        self.status = CustomerStatus.ACTIVE
        self._record_event(
            CustomerActivated(customer_id=self.customer_id, activated_at=_utc_now())
        )

    def suspend(self, *, reason: str) -> None:
        if self.status is not CustomerStatus.ACTIVE:
            raise DomainRuleViolation("Cannot suspend a customer that is not active")

        self.status = CustomerStatus.SUSPENDED
        self._record_event(
            CustomerSuspended(
                customer_id=self.customer_id,
                suspended_at=_utc_now(),
                reason=reason,
            )
        )

    def resolve_suspension(self) -> None:
        if self.status is not CustomerStatus.SUSPENDED:
            raise DomainRuleViolation(
                "Cannot resolve suspension for a customer that is not suspended"
            )

        self.status = CustomerStatus.ACTIVE
        self._record_event(
            CustomerSuspensionResolved(
                customer_id=self.customer_id,
                resolved_at=_utc_now(),
            )
        )

    def update_info(self, *, name: str | None = None, phone: str | None = None) -> None:
        updated_fields: list[str] = []

        if name is not None and name != self.name:
            if not name.strip():
                raise ValueError("Customer name is required")
            self.name = name
            updated_fields.append("name")

        if phone is not None and phone != self.phone:
            self.phone = phone
            updated_fields.append("phone")

        if updated_fields:
            self._record_event(
                CustomerInfoUpdated(
                    customer_id=self.customer_id,
                    updated_fields=updated_fields,
                )
            )

    def pull_domain_events(self) -> list[Any]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    def _record_event(self, event: Any) -> None:
        self._domain_events.append(event)
