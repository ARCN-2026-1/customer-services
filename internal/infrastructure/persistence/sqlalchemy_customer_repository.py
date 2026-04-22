from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from internal.domain.entities.customer import Customer
from internal.domain.valueobjects.customer_role import CustomerRole
from internal.domain.valueobjects.customer_status import CustomerStatus
from internal.domain.valueobjects.email import Email
from internal.infrastructure.persistence.models import CustomerModel


class SqlAlchemyCustomerRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def add(self, customer: Customer) -> None:
        with self._session_factory() as session:
            session.add(self._to_model(customer))
            try:
                session.commit()
            except IntegrityError as error:
                session.rollback()
                raise ValueError(
                    f"Customer with email {customer.email.value} already exists"
                ) from error

    def save(self, customer: Customer) -> None:
        with self._session_factory() as session:
            model = session.get(CustomerModel, str(customer.customer_id))
            if model is None:
                session.add(self._to_model(customer))
            else:
                model.name = customer.name
                model.email = customer.email.value
                model.phone = customer.phone
                model.password_hash = customer.password_hash
                model.status = customer.status.value
                model.role = customer.role.value
                model.registered_at = customer.registered_at
            session.commit()

    def get_by_id(self, customer_id: UUID) -> Customer | None:
        with self._session_factory() as session:
            model = session.get(CustomerModel, str(customer_id))
            return None if model is None else self._to_domain(model)

    def get_by_email(self, email: str) -> Customer | None:
        normalized_email = email.strip().lower()
        with self._session_factory() as session:
            model = (
                session.query(CustomerModel)
                .filter(CustomerModel.email == normalized_email)
                .one_or_none()
            )
            return None if model is None else self._to_domain(model)

    def list_all(self) -> list[Customer]:
        with self._session_factory() as session:
            models = (
                session.query(CustomerModel).order_by(CustomerModel.email.asc()).all()
            )
            return [self._to_domain(model) for model in models]

    def _to_model(self, customer: Customer) -> CustomerModel:
        return CustomerModel(
            customer_id=str(customer.customer_id),
            name=customer.name,
            email=customer.email.value,
            phone=customer.phone,
            password_hash=customer.password_hash,
            status=customer.status.value,
            role=customer.role.value,
            registered_at=customer.registered_at,
        )

    def _to_domain(self, model: CustomerModel) -> Customer:
        return Customer(
            customer_id=UUID(model.customer_id),
            name=model.name,
            email=Email(model.email),
            phone=model.phone,
            password_hash=model.password_hash,
            status=CustomerStatus(model.status),
            role=CustomerRole(model.role),
            registered_at=model.registered_at,
        )
