from internal.application.commands.update_customer_info import UpdateCustomerInfoCommand
from internal.application.dto.customer import CustomerDTO
from internal.application.usecases._shared import (
    get_existing_customer,
    publish_domain_events,
    to_customer_dto,
)
from internal.domain.repositories.customer_repository import CustomerRepository
from internal.domain.services.event_publisher import EventPublisher


class UpdateCustomerInfo:
    def __init__(
        self, repository: CustomerRepository, event_publisher: EventPublisher
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    def execute(self, command: UpdateCustomerInfoCommand) -> CustomerDTO:
        customer = get_existing_customer(self._repository, command.customer_id)
        customer.update_info(name=command.name, phone=command.phone)
        self._repository.save(customer)
        publish_domain_events(self._event_publisher, customer.pull_domain_events())
        return to_customer_dto(customer)
