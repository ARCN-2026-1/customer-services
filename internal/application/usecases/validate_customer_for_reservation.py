from internal.application.dto.customer import ReservationEligibilityDTO
from internal.application.usecases._shared import get_existing_customer
from internal.domain.repositories.customer_repository import CustomerRepository


class ValidateCustomerForReservation:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    def execute(self, customer_id: str) -> ReservationEligibilityDTO:
        customer = get_existing_customer(self._repository, customer_id)
        return ReservationEligibilityDTO(
            customer_id=str(customer.customer_id),
            status=customer.status.value,
            is_eligible=customer.is_eligible_for_reservation,
        )
