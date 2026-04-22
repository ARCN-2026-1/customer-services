from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SuspendCustomerCommand:
    customer_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ResolveCustomerSuspensionCommand:
    customer_id: str


@dataclass(frozen=True, slots=True)
class DeactivateCustomerCommand:
    customer_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ActivateCustomerCommand:
    customer_id: str
