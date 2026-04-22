from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from internal.application.commands.authenticate_customer import (
    AuthenticateCustomerCommand,
)
from internal.application.commands.change_customer_status import (
    ActivateCustomerCommand,
    DeactivateCustomerCommand,
    ResolveCustomerSuspensionCommand,
    SuspendCustomerCommand,
)
from internal.application.commands.register_customer import RegisterCustomerCommand
from internal.application.commands.update_customer_info import UpdateCustomerInfoCommand
from internal.application.errors import (
    AuthenticationFailedError,
    CustomerAlreadyExistsError,
    CustomerNotFoundError,
    EventPublicationError,
)
from internal.application.usecases.authenticate_customer import AuthenticateCustomer
from internal.application.usecases.change_customer_status import (
    ActivateCustomer,
    DeactivateCustomer,
    ResolveCustomerSuspension,
    SuspendCustomer,
)
from internal.application.usecases.get_customer_by_id import GetCustomerById
from internal.application.usecases.list_customers import ListCustomers
from internal.application.usecases.register_customer import RegisterCustomer
from internal.application.usecases.update_customer_info import UpdateCustomerInfo
from internal.application.usecases.validate_customer_for_reservation import (
    ValidateCustomerForReservation,
)
from internal.domain.entities.customer import Customer
from internal.domain.valueobjects.customer_role import CustomerRole
from internal.domain.valueobjects.customer_status import CustomerStatus
from internal.domain.valueobjects.email import Email


def test_When_RegisteringNewCustomer_Expect_CustomerPersistedAndTokenReturned() -> None:
    # Arrange
    repository = InMemoryCustomerRepository()
    event_publisher = InMemoryEventPublisher()
    password_hasher = FakePasswordHasher()
    token_generator = FakeTokenGenerator()
    use_case = RegisterCustomer(
        repository, password_hasher, token_generator, event_publisher
    )

    # Act
    result = use_case.execute(
        RegisterCustomerCommand(
            name="Jane Doe",
            email="jane@example.com",
            phone="+57-3000000000",
            password="plain-password",
        )
    )

    # Assert
    persisted_customer = repository.get_by_email("jane@example.com")
    assert persisted_customer is not None
    assert persisted_customer.password_hash == "hashed::plain-password"
    assert result.access_token == f"token::{persisted_customer.customer_id}::customer"
    assert result.customer.email == "jane@example.com"
    assert not hasattr(result.customer, "password_hash")
    assert [event.event_name for event in event_publisher.events] == [
        "CustomerRegistered"
    ]


def test_When_RegisteringDuplicatedEmail_Expect_RegistrationToFail() -> None:
    # Arrange
    existing_customer = build_customer(email="jane@example.com")
    repository = InMemoryCustomerRepository(customers=[existing_customer])
    use_case = RegisterCustomer(
        repository,
        FakePasswordHasher(),
        FakeTokenGenerator(),
        InMemoryEventPublisher(),
    )

    # Act / Assert
    with pytest.raises(CustomerAlreadyExistsError, match="already exists"):
        use_case.execute(
            RegisterCustomerCommand(
                name="Jane Doe",
                email="jane@example.com",
                phone="+57-3000000000",
                password="plain-password",
            )
        )


def test_When_AuthenticatingActiveCustomer_Expect_TokenReturned() -> None:
    # Arrange
    customer = build_customer(status=CustomerStatus.ACTIVE)
    repository = InMemoryCustomerRepository(customers=[customer])
    use_case = AuthenticateCustomer(
        repository,
        FakePasswordHasher(),
        FakeTokenGenerator(),
    )

    # Act
    result = use_case.execute(
        AuthenticateCustomerCommand(
            email=customer.email.value, password="plain-password"
        )
    )

    # Assert
    assert result.access_token == f"token::{customer.customer_id}::customer"
    assert result.customer.customer_id == str(customer.customer_id)
    assert result.customer.status == "ACTIVE"


def test_When_AuthenticatingSuspendedCustomer_Expect_LoginToFail() -> None:
    # Arrange
    customer = build_customer(status=CustomerStatus.SUSPENDED)
    repository = InMemoryCustomerRepository(customers=[customer])
    use_case = AuthenticateCustomer(
        repository,
        FakePasswordHasher(),
        FakeTokenGenerator(),
    )

    # Act / Assert
    with pytest.raises(AuthenticationFailedError, match="suspended"):
        use_case.execute(
            AuthenticateCustomerCommand(
                email=customer.email.value, password="plain-password"
            )
        )


def test_When_AuthenticatingInactiveCustomer_Expect_LoginToFail() -> None:
    # Arrange
    customer = build_customer(status=CustomerStatus.INACTIVE)
    repository = InMemoryCustomerRepository(customers=[customer])
    use_case = AuthenticateCustomer(
        repository,
        FakePasswordHasher(),
        FakeTokenGenerator(),
    )

    # Act / Assert
    with pytest.raises(AuthenticationFailedError, match="inactive"):
        use_case.execute(
            AuthenticateCustomerCommand(
                email=customer.email.value, password="plain-password"
            )
        )


def test_When_PasswordDoesNotMatch_Expect_LoginToFail() -> None:
    # Arrange
    customer = build_customer(status=CustomerStatus.ACTIVE)
    repository = InMemoryCustomerRepository(customers=[customer])
    use_case = AuthenticateCustomer(
        repository,
        FakePasswordHasher(valid_password="different-password"),
        FakeTokenGenerator(),
    )

    # Act / Assert
    with pytest.raises(AuthenticationFailedError, match="Invalid credentials"):
        use_case.execute(
            AuthenticateCustomerCommand(
                email=customer.email.value, password="plain-password"
            )
        )


def test_When_SuspendingActiveCustomer_Expect_StatusUpdatedAndEventPublished() -> None:
    # Arrange
    customer = build_customer(status=CustomerStatus.ACTIVE)
    repository = InMemoryCustomerRepository(customers=[customer])
    event_publisher = InMemoryEventPublisher()
    use_case = SuspendCustomer(repository, event_publisher)

    # Act
    result = use_case.execute(
        SuspendCustomerCommand(
            customer_id=str(customer.customer_id), reason="manual_review"
        )
    )

    # Assert
    assert result.status == "SUSPENDED"
    assert repository.saved_customers[-1].status is CustomerStatus.SUSPENDED
    assert [event.event_name for event in event_publisher.events] == [
        "CustomerSuspended"
    ]


def test_When_ResolvingSuspendedCustomer_Expect_StatusUpdatedAndEventPublished() -> (
    None
):
    # Arrange
    customer = build_customer(status=CustomerStatus.SUSPENDED)
    repository = InMemoryCustomerRepository(customers=[customer])
    event_publisher = InMemoryEventPublisher()
    use_case = ResolveCustomerSuspension(repository, event_publisher)

    # Act
    result = use_case.execute(
        ResolveCustomerSuspensionCommand(customer_id=str(customer.customer_id))
    )

    # Assert
    assert result.status == "ACTIVE"
    assert repository.saved_customers[-1].status is CustomerStatus.ACTIVE
    assert [event.event_name for event in event_publisher.events] == [
        "CustomerSuspensionResolved"
    ]


def test_When_DeactivatingActiveCustomer_Expect_StatusUpdatedAndEventPublished() -> (
    None
):
    # Arrange
    customer = build_customer(status=CustomerStatus.ACTIVE)
    repository = InMemoryCustomerRepository(customers=[customer])
    event_publisher = InMemoryEventPublisher()
    use_case = DeactivateCustomer(repository, event_publisher)

    # Act
    result = use_case.execute(
        DeactivateCustomerCommand(
            customer_id=str(customer.customer_id), reason="manual"
        )
    )

    # Assert
    assert result.status == "INACTIVE"
    assert repository.saved_customers[-1].status is CustomerStatus.INACTIVE
    assert [event.event_name for event in event_publisher.events] == [
        "CustomerDeactivated"
    ]


def test_When_ActivatingInactiveCustomer_Expect_StatusUpdatedAndEventPublished() -> (
    None
):
    # Arrange
    customer = build_customer(status=CustomerStatus.INACTIVE)
    repository = InMemoryCustomerRepository(customers=[customer])
    event_publisher = InMemoryEventPublisher()
    use_case = ActivateCustomer(repository, event_publisher)

    # Act
    result = use_case.execute(
        ActivateCustomerCommand(customer_id=str(customer.customer_id))
    )

    # Assert
    assert result.status == "ACTIVE"
    assert repository.saved_customers[-1].status is CustomerStatus.ACTIVE
    assert [event.event_name for event in event_publisher.events] == [
        "CustomerActivated"
    ]


def test_When_UpdatingCustomerInfo_Expect_UpdatedCustomerReturnedWithoutPasswordHash() -> (
    None
):
    # Arrange
    customer = build_customer(name="Jane Doe", phone="+57-3000000000")
    repository = InMemoryCustomerRepository(customers=[customer])
    event_publisher = InMemoryEventPublisher()
    use_case = UpdateCustomerInfo(repository, event_publisher)

    # Act
    result = use_case.execute(
        UpdateCustomerInfoCommand(
            customer_id=str(customer.customer_id),
            name="Jane Roe",
            phone="+57-3111111111",
        )
    )

    # Assert
    assert result.name == "Jane Roe"
    assert result.phone == "+57-3111111111"
    assert not hasattr(result, "password_hash")
    assert [event.event_name for event in event_publisher.events] == [
        "CustomerInfoUpdated"
    ]


def test_When_RegisteringCustomerPublishFails_Expect_EventPublicationError() -> None:
    # Arrange
    repository = InMemoryCustomerRepository()
    event_publisher = FailingEventPublisher()
    use_case = RegisterCustomer(
        repository,
        FakePasswordHasher(),
        FakeTokenGenerator(),
        event_publisher,
    )

    # Act / Assert
    with pytest.raises(EventPublicationError, match="publish failed"):
        use_case.execute(
            RegisterCustomerCommand(
                name="Jane Doe",
                email="jane@example.com",
                phone="+57-3000000000",
                password="plain-password",
            )
        )


def test_When_SuspendingCustomerPublishFails_Expect_EventPublicationError() -> None:
    # Arrange
    customer = build_customer(status=CustomerStatus.ACTIVE)
    repository = InMemoryCustomerRepository(customers=[customer])
    use_case = SuspendCustomer(repository, FailingEventPublisher())

    # Act / Assert
    with pytest.raises(EventPublicationError, match="publish failed"):
        use_case.execute(
            SuspendCustomerCommand(
                customer_id=str(customer.customer_id), reason="manual_review"
            )
        )


def test_When_GettingExistingCustomer_Expect_CustomerReturnedWithoutPasswordHash() -> (
    None
):
    # Arrange
    customer = build_customer()
    repository = InMemoryCustomerRepository(customers=[customer])
    use_case = GetCustomerById(repository)

    # Act
    result = use_case.execute(str(customer.customer_id))

    # Assert
    assert result.customer_id == str(customer.customer_id)
    assert result.email == customer.email.value
    assert not hasattr(result, "password_hash")


def test_When_GettingMissingCustomer_Expect_NotFoundError() -> None:
    # Arrange
    repository = InMemoryCustomerRepository()
    use_case = GetCustomerById(repository)

    # Act / Assert
    with pytest.raises(CustomerNotFoundError):
        use_case.execute(str(uuid4()))


def test_When_ValidatingActiveCustomerForReservation_Expect_EligibleResponse() -> None:
    # Arrange
    customer = build_customer(status=CustomerStatus.ACTIVE)
    repository = InMemoryCustomerRepository(customers=[customer])
    use_case = ValidateCustomerForReservation(repository)

    # Act
    result = use_case.execute(str(customer.customer_id))

    # Assert
    assert result.customer_id == str(customer.customer_id)
    assert result.status == "ACTIVE"
    assert result.is_eligible is True


def test_When_ListingCustomers_Expect_AllCustomersReturnedWithoutPasswordHash() -> None:
    # Arrange
    customers = [
        build_customer(name="Jane Doe", email="jane@example.com"),
        build_customer(name="John Doe", email="john@example.com"),
    ]
    repository = InMemoryCustomerRepository(customers=customers)
    use_case = ListCustomers(repository)

    # Act
    result = use_case.execute()

    # Assert
    assert [customer.email for customer in result] == [
        "jane@example.com",
        "john@example.com",
    ]
    assert all(not hasattr(customer, "password_hash") for customer in result)


@dataclass
class InMemoryEventPublisher:
    events: list[object] = None

    def __post_init__(self) -> None:
        if self.events is None:
            self.events = []

    def publish(self, event: object) -> None:
        self.events.append(event)


class FailingEventPublisher:
    def publish(self, event: object) -> None:
        raise EventPublicationError("publish failed")


@dataclass
class FakePasswordHasher:
    valid_password: str = "plain-password"

    def hash(self, plain_password: str) -> str:
        return f"hashed::{plain_password}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return plain_password == self.valid_password and hashed_password.startswith(
            "hashed::"
        )


class FakeTokenGenerator:
    def generate(self, *, customer_id: str, role: str) -> str:
        return f"token::{customer_id}::{role}"

    def validate(self, token: str) -> dict[str, str]:
        _, customer_id, role = token.split("::")
        return {"sub": customer_id, "role": role}


class InMemoryCustomerRepository:
    def __init__(self, customers: list[Customer] | None = None) -> None:
        self._customers_by_id = {
            customer.customer_id: customer for customer in customers or []
        }
        self.saved_customers: list[Customer] = []

    def add(self, customer: Customer) -> None:
        self._customers_by_id[customer.customer_id] = customer
        self.saved_customers.append(customer)

    def save(self, customer: Customer) -> None:
        self._customers_by_id[customer.customer_id] = customer
        self.saved_customers.append(customer)

    def get_by_id(self, customer_id: UUID) -> Customer | None:
        return self._customers_by_id.get(customer_id)

    def get_by_email(self, email: str) -> Customer | None:
        normalized_email = email.strip().lower()
        return next(
            (
                customer
                for customer in self._customers_by_id.values()
                if customer.email.value == normalized_email
            ),
            None,
        )

    def list_all(self) -> list[Customer]:
        return list(self._customers_by_id.values())


def build_customer(
    *,
    name: str = "Jane Doe",
    email: str = "jane@example.com",
    phone: str | None = "+57-3000000000",
    status: CustomerStatus = CustomerStatus.ACTIVE,
) -> Customer:
    return Customer(
        customer_id=uuid4(),
        name=name,
        email=Email(email),
        phone=phone,
        password_hash="hashed::plain-password",
        status=status,
        role=CustomerRole.CUSTOMER,
        registered_at=datetime(2026, 4, 21, tzinfo=timezone.utc),
    )
