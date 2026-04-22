from uuid import UUID

from internal.application.dto.customer import CustomerDTO
from internal.application.errors import CustomerNotFoundError, EventPublicationError
from internal.domain.entities.customer import Customer
from internal.domain.repositories.customer_repository import CustomerRepository
from internal.domain.services.event_publisher import EventPublisher


def to_customer_dto(customer: Customer) -> CustomerDTO:
    return CustomerDTO(
        customer_id=str(customer.customer_id),
        name=customer.name,
        email=customer.email.value,
        phone=customer.phone,
        status=customer.status.value,
        role=customer.role.value,
    )


def get_existing_customer(repository: CustomerRepository, customer_id: str) -> Customer:
    customer = repository.get_by_id(UUID(customer_id))
    if customer is None:
        raise CustomerNotFoundError(f"Customer {customer_id} was not found")
    return customer


def publish_domain_events(
    event_publisher: EventPublisher, events: list[object]
) -> None:
    try:
        for event in events:
            event_publisher.publish(event)
    except EventPublicationError:
        raise
    except Exception as error:
        raise EventPublicationError("Customer event publication failed") from error
