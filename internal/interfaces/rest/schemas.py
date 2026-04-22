from pydantic import BaseModel, ConfigDict, EmailStr, Field

EXAMPLE_CUSTOMER_EMAIL = "jane@example.com"


def _to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelCaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)


class RegisterCustomerRequest(CamelCaseModel):
    name: str = Field(
        description="Customer full name",
        examples=["Jane Doe"],
    )
    email: EmailStr = Field(
        description="Unique customer email address",
        examples=[EXAMPLE_CUSTOMER_EMAIL],
    )
    phone: str | None = Field(
        default=None,
        description="Customer contact phone number",
        examples=["+57-3000000000"],
    )
    password: str = Field(
        description="Plain password used only during registration or login",
        examples=["plain-password"],
        min_length=8,
    )


class LoginRequest(CamelCaseModel):
    email: EmailStr = Field(
        description="Registered customer email address",
        examples=[EXAMPLE_CUSTOMER_EMAIL],
    )
    password: str = Field(
        description="Plain password for authentication",
        examples=["plain-password"],
    )


class UpdateCustomerRequest(CamelCaseModel):
    name: str | None = Field(
        default=None,
        description="Updated customer full name",
        examples=["Jane Admin Update"],
    )
    phone: str | None = Field(
        default=None,
        description="Updated customer contact phone number",
        examples=["+57-3222222222"],
    )


class ChangeStatusRequest(CamelCaseModel):
    reason: str = Field(
        description="Business reason for the administrative status change",
        examples=["manual_review"],
    )


class ErrorResponse(CamelCaseModel):
    detail: str = Field(
        description="Human-readable error description",
        examples=["Customer not found"],
    )


class CustomerResponse(CamelCaseModel):
    customer_id: str = Field(
        description="Unique customer identifier",
        examples=["8e4d9f62-10e5-4d77-9cc3-4d226472df1e"],
    )
    name: str = Field(description="Customer full name", examples=["Jane Doe"])
    email: str = Field(
        description="Customer email address",
        examples=[EXAMPLE_CUSTOMER_EMAIL],
    )
    phone: str | None = Field(
        default=None,
        description="Customer contact phone number",
        examples=["+57-3000000000"],
    )
    status: str = Field(
        description="Current customer lifecycle status",
        examples=["ACTIVE"],
    )
    role: str = Field(
        description="Current customer role within the MVP auth model",
        examples=["customer"],
    )


class AuthenticationResponse(CamelCaseModel):
    access_token: str = Field(
        description="JWT access token for authenticated requests",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        description="Authentication scheme returned by the API",
        examples=["Bearer"],
    )
    expires_in: int = Field(
        description="Access token lifetime in seconds",
        examples=[1800],
    )
    customer: CustomerResponse = Field(
        description="Authenticated customer profile",
    )


class ReservationEligibilityResponse(CamelCaseModel):
    customer_id: str = Field(
        description="Customer identifier used for the eligibility check",
        examples=["8e4d9f62-10e5-4d77-9cc3-4d226472df1e"],
    )
    status: str = Field(
        description="Current customer lifecycle status",
        examples=["ACTIVE"],
    )
    is_eligible: bool = Field(
        description="Whether the customer can create a reservation",
        examples=[True],
    )
