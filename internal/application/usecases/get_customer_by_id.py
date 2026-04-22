from internal.application.dto.customer import CustomerDTO
from internal.application.usecases._shared import get_existing_customer, to_customer_dto
from internal.domain.repositories.customer_repository import CustomerRepository


class GetCustomerById:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    def execute(self, customer_id: str) -> CustomerDTO:
        customer = get_existing_customer(self._repository, customer_id)
        return to_customer_dto(customer)
