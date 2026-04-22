from internal.application.commands.change_customer_status import (
    ActivateCustomerCommand,
    DeactivateCustomerCommand,
    ResolveCustomerSuspensionCommand,
    SuspendCustomerCommand,
)
from internal.application.dto.customer import CustomerDTO
from internal.application.usecases._shared import (
    get_existing_customer,
    publish_domain_events,
    to_customer_dto,
)
from internal.domain.repositories.customer_repository import CustomerRepository
from internal.domain.services.event_publisher import EventPublisher


class SuspendCustomer:
    def __init__(
        self, repository: CustomerRepository, event_publisher: EventPublisher
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    def execute(self, command: SuspendCustomerCommand) -> CustomerDTO:
        customer = get_existing_customer(self._repository, command.customer_id)
        customer.suspend(reason=command.reason)
        self._repository.save(customer)
        publish_domain_events(self._event_publisher, customer.pull_domain_events())
        return to_customer_dto(customer)


class ResolveCustomerSuspension:
    def __init__(
        self, repository: CustomerRepository, event_publisher: EventPublisher
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    def execute(self, command: ResolveCustomerSuspensionCommand) -> CustomerDTO:
        customer = get_existing_customer(self._repository, command.customer_id)
        customer.resolve_suspension()
        self._repository.save(customer)
        publish_domain_events(self._event_publisher, customer.pull_domain_events())
        return to_customer_dto(customer)


class DeactivateCustomer:
    def __init__(
        self, repository: CustomerRepository, event_publisher: EventPublisher
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    def execute(self, command: DeactivateCustomerCommand) -> CustomerDTO:
        customer = get_existing_customer(self._repository, command.customer_id)
        customer.deactivate(reason=command.reason)
        self._repository.save(customer)
        publish_domain_events(self._event_publisher, customer.pull_domain_events())
        return to_customer_dto(customer)


class ActivateCustomer:
    def __init__(
        self, repository: CustomerRepository, event_publisher: EventPublisher
    ) -> None:
        self._repository = repository
        self._event_publisher = event_publisher

    def execute(self, command: ActivateCustomerCommand) -> CustomerDTO:
        customer = get_existing_customer(self._repository, command.customer_id)
        customer.activate()
        self._repository.save(customer)
        publish_domain_events(self._event_publisher, customer.pull_domain_events())
        return to_customer_dto(customer)
