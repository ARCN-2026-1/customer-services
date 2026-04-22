from internal.application.commands.authenticate_customer import (
    AuthenticateCustomerCommand,
)
from internal.application.dto.customer import AuthenticationResultDTO
from internal.application.errors import AuthenticationFailedError
from internal.application.usecases._shared import to_customer_dto
from internal.domain.repositories.customer_repository import CustomerRepository
from internal.domain.services.password_hasher import PasswordHasher
from internal.domain.services.token_generator import TokenGenerator
from internal.domain.valueobjects.customer_status import CustomerStatus


class AuthenticateCustomer:
    def __init__(
        self,
        repository: CustomerRepository,
        password_hasher: PasswordHasher,
        token_generator: TokenGenerator,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._token_generator = token_generator

    def execute(self, command: AuthenticateCustomerCommand) -> AuthenticationResultDTO:
        customer = self._repository.get_by_email(command.email)
        if customer is None:
            raise AuthenticationFailedError("Invalid credentials")

        if customer.status is CustomerStatus.SUSPENDED:
            raise AuthenticationFailedError("Customer account is suspended")
        if customer.status is CustomerStatus.INACTIVE:
            raise AuthenticationFailedError("Customer account is inactive")
        if not self._password_hasher.verify(command.password, customer.password_hash):
            raise AuthenticationFailedError("Invalid credentials")

        return AuthenticationResultDTO(
            access_token=self._token_generator.generate(
                customer_id=str(customer.customer_id), role=customer.role.value
            ),
            token_type="Bearer",
            expires_in=1800,
            customer=to_customer_dto(customer),
        )
