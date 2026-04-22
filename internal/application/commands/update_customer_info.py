from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UpdateCustomerInfoCommand:
    customer_id: str
    name: str | None = None
    phone: str | None = None
