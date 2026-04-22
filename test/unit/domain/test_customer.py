from datetime import datetime, timezone
from uuid import uuid4

import pytest

from internal.domain.entities.customer import Customer
from internal.domain.errors import DomainRuleViolation
from internal.domain.valueobjects.customer_role import CustomerRole
from internal.domain.valueobjects.customer_status import CustomerStatus
from internal.domain.valueobjects.email import Email


def test_When_CustomerIsRegistered_Expect_InitialStateAndRegisteredEvent() -> None:
    # Arrange
    registered_at = datetime(2026, 4, 21, tzinfo=timezone.utc)

    # Act
    customer = Customer.register(
        customer_id=uuid4(),
        name="Jane Doe",
        email=Email("jane@example.com"),
        phone="+57-3000000000",
        password_hash="hashed-password",
        registered_at=registered_at,
    )
    events = customer.pull_domain_events()

    # Assert
    assert customer.status is CustomerStatus.ACTIVE
    assert customer.role is CustomerRole.CUSTOMER
    assert customer.is_eligible_for_reservation is True
    assert events[0].event_name == "CustomerRegistered"
    assert events[0].customer_id == customer.customer_id


def test_When_EmailIsInvalid_Expect_CustomerRegistrationToFail() -> None:
    # Arrange
    invalid_email = "jane-at-example.com"

    # Act / Assert
    with pytest.raises(ValueError, match="valid email"):
        Email(invalid_email)


def test_When_CustomerIsActive_Expect_DeactivateToMoveToInactive() -> None:
    # Arrange
    customer = _build_customer(status=CustomerStatus.ACTIVE)

    # Act
    customer.deactivate(reason="manual")
    events = customer.pull_domain_events()

    # Assert
    assert customer.status is CustomerStatus.INACTIVE
    assert customer.is_eligible_for_reservation is False
    assert events[0].event_name == "CustomerDeactivated"


def test_When_CustomerIsSuspended_Expect_DeactivateToFail() -> None:
    # Arrange
    customer = _build_customer(status=CustomerStatus.SUSPENDED)

    # Act / Assert
    with pytest.raises(
        DomainRuleViolation, match="Cannot deactivate a suspended customer"
    ):
        customer.deactivate(reason="manual")


def test_When_CustomerIsInactive_Expect_ActivateToMoveToActive() -> None:
    # Arrange
    customer = _build_customer(status=CustomerStatus.INACTIVE)

    # Act
    customer.activate()
    events = customer.pull_domain_events()

    # Assert
    assert customer.status is CustomerStatus.ACTIVE
    assert customer.is_eligible_for_reservation is True
    assert events[0].event_name == "CustomerActivated"


def test_When_CustomerIsSuspended_Expect_ActivateToFail() -> None:
    # Arrange
    customer = _build_customer(status=CustomerStatus.SUSPENDED)

    # Act / Assert
    with pytest.raises(
        DomainRuleViolation, match="Cannot activate a customer that is not inactive"
    ):
        customer.activate()


def test_When_CustomerIsActive_Expect_SuspendToMoveToSuspended() -> None:
    # Arrange
    customer = _build_customer(status=CustomerStatus.ACTIVE)

    # Act
    customer.suspend(reason="policy_violation")
    events = customer.pull_domain_events()

    # Assert
    assert customer.status is CustomerStatus.SUSPENDED
    assert customer.is_eligible_for_reservation is False
    assert events[0].event_name == "CustomerSuspended"


def test_When_CustomerIsInactive_Expect_SuspendToFail() -> None:
    # Arrange
    customer = _build_customer(status=CustomerStatus.INACTIVE)

    # Act / Assert
    with pytest.raises(
        DomainRuleViolation, match="Cannot suspend a customer that is not active"
    ):
        customer.suspend(reason="policy_violation")


def test_When_CustomerIsSuspended_Expect_ResolveSuspensionToMoveToActive() -> None:
    # Arrange
    customer = _build_customer(status=CustomerStatus.SUSPENDED)

    # Act
    customer.resolve_suspension()
    events = customer.pull_domain_events()

    # Assert
    assert customer.status is CustomerStatus.ACTIVE
    assert customer.is_eligible_for_reservation is True
    assert events[0].event_name == "CustomerSuspensionResolved"


def test_When_CustomerIsInactive_Expect_ResolveSuspensionToFail() -> None:
    # Arrange
    customer = _build_customer(status=CustomerStatus.INACTIVE)

    # Act / Assert
    with pytest.raises(
        DomainRuleViolation,
        match="Cannot resolve suspension for a customer that is not suspended",
    ):
        customer.resolve_suspension()


def test_When_CustomerInfoChanges_Expect_UpdateToEmitChangedFieldsEvent() -> None:
    # Arrange
    customer = _build_customer()

    # Act
    customer.update_info(name="Jane Roe", phone="+57-3111111111")
    events = customer.pull_domain_events()

    # Assert
    assert customer.name == "Jane Roe"
    assert customer.phone == "+57-3111111111"
    assert events[0].event_name == "CustomerInfoUpdated"
    assert events[0].updated_fields == ["name", "phone"]


def _build_customer(status: CustomerStatus = CustomerStatus.ACTIVE) -> Customer:
    return Customer(
        customer_id=uuid4(),
        name="Jane Doe",
        email=Email("jane@example.com"),
        phone="+57-3000000000",
        password_hash="hashed-password",
        status=status,
        role=CustomerRole.CUSTOMER,
        registered_at=datetime(2026, 4, 21, tzinfo=timezone.utc),
    )
