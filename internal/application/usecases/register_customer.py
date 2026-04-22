from datetime import datetime, timezone
from uuid import uuid4

from internal.application.commands.register_customer import RegisterCustomerCommand
from internal.application.dto.customer import AuthenticationResultDTO
from internal.application.errors import CustomerAlreadyExistsError
from internal.application.usecases._shared import publish_domain_events, to_customer_dto
from internal.domain.entities.customer import Customer
from internal.domain.repositories.customer_repository import CustomerRepository
from internal.domain.services.event_publisher import EventPublisher
from internal.domain.services.password_hasher import PasswordHasher
from internal.domain.services.token_generator import TokenGenerator
from internal.domain.valueobjects.email import Email


class RegisterCustomer:
    def __init__(
        self,
        repository: CustomerRepository,
        password_hasher: PasswordHasher,
        token_generator: TokenGenerator,
        event_publisher: EventPublisher,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._token_generator = token_generator
        self._event_publisher = event_publisher

    def execute(self, command: RegisterCustomerCommand) -> AuthenticationResultDTO:
        if self._repository.get_by_email(command.email) is not None:
            raise CustomerAlreadyExistsError(
                f"Customer with email {command.email} already exists"
            )

        customer = Customer.register(
            customer_id=uuid4(),
            name=command.name,
            email=Email(command.email),
            phone=command.phone,
            password_hash=self._password_hasher.hash(command.password),
            registered_at=datetime.now(timezone.utc),
        )
        self._repository.add(customer)
        publish_domain_events(self._event_publisher, customer.pull_domain_events())

        return AuthenticationResultDTO(
            access_token=self._token_generator.generate(
                customer_id=str(customer.customer_id), role=customer.role.value
            ),
            token_type="Bearer",
            expires_in=1800,
            customer=to_customer_dto(customer),
        )
