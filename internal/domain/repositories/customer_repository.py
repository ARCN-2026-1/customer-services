from __future__ import annotations

from typing import Protocol
from uuid import UUID

from internal.domain.entities.customer import Customer


class CustomerRepository(Protocol):
    def add(self, customer: Customer) -> None: ...

    def save(self, customer: Customer) -> None: ...

    def get_by_id(self, customer_id: UUID) -> Customer | None: ...

    def get_by_email(self, email: str) -> Customer | None: ...

    def list_all(self) -> list[Customer]: ...
