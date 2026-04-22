from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegisterCustomerCommand:
    name: str
    email: str
    phone: str | None
    password: str
