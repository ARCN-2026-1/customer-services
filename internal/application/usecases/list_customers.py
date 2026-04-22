from internal.application.dto.customer import CustomerDTO
from internal.application.usecases._shared import to_customer_dto
from internal.domain.repositories.customer_repository import CustomerRepository


class ListCustomers:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    def execute(self) -> list[CustomerDTO]:
        return [to_customer_dto(customer) for customer in self._repository.list_all()]
