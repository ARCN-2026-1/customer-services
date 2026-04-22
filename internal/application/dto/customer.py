from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CustomerDTO:
    customer_id: str
    name: str
    email: str
    phone: str | None
    status: str
    role: str


@dataclass(frozen=True, slots=True)
class ReservationEligibilityDTO:
    customer_id: str
    status: str
    is_eligible: bool


@dataclass(frozen=True, slots=True)
class AuthenticationResultDTO:
    access_token: str
    token_type: str
    expires_in: int
    customer: CustomerDTO
