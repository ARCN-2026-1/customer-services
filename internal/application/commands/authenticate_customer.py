from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticateCustomerCommand:
    email: str
    password: str
