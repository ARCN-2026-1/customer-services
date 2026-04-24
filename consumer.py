from __future__ import annotations

from dataclasses import dataclass
import logging

from internal.application.usecases.validate_customer_for_reservation import (
    ValidateCustomerForReservation,
)
from internal.infrastructure.config.settings import CustomerServiceSettings
from internal.infrastructure.messaging.factory import (
    create_customer_validation_consumer,
    create_event_publisher,
)
from internal.infrastructure.persistence.sqlalchemy_customer_repository import (
    SqlAlchemyCustomerRepository,
)
from internal.infrastructure.persistence.unit_of_work import create_session_factory
from internal.interfaces.messaging.customer_validation_consumer import (
    CustomerValidationConsumer,
)


@dataclass(frozen=True, slots=True)
class WorkerRuntime:
    settings: CustomerServiceSettings
    repository: SqlAlchemyCustomerRepository
    handler: CustomerValidationConsumer
    event_publisher: object
    consumer: object


def build_worker_runtime(
    settings: CustomerServiceSettings | None = None,
) -> WorkerRuntime:
    resolved_settings = settings or CustomerServiceSettings()
    session_factory = create_session_factory(resolved_settings.resolved_database_url)
    repository = SqlAlchemyCustomerRepository(session_factory)
    handler = CustomerValidationConsumer(ValidateCustomerForReservation(repository))
    event_publisher = create_event_publisher(resolved_settings)
    consumer = create_customer_validation_consumer(
        settings=resolved_settings,
        handler=handler,
        event_publisher=event_publisher,
    )
    return WorkerRuntime(
        settings=resolved_settings,
        repository=repository,
        handler=handler,
        event_publisher=event_publisher,
        consumer=consumer,
    )


def _configure_logging() -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=logging.INFO)
        return

    root_logger.setLevel(logging.INFO)


def main() -> None:
    _configure_logging()
    runtime = build_worker_runtime()
    runtime.consumer.ensure_topology()
    runtime.consumer.start_consuming()


if __name__ == "__main__":
    main()
