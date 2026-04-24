import logging
from functools import partial
from typing import Any

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from internal.application.commands.authenticate_customer import (
    AuthenticateCustomerCommand,
)
from internal.application.commands.change_customer_status import (
    ActivateCustomerCommand,
    DeactivateCustomerCommand,
    ResolveCustomerSuspensionCommand,
    SuspendCustomerCommand,
)
from internal.application.commands.register_customer import RegisterCustomerCommand
from internal.application.commands.update_customer_info import UpdateCustomerInfoCommand
from internal.application.errors import (
    ApplicationError,
    AuthenticationFailedError,
    AuthorizationDeniedError,
    CustomerAlreadyExistsError,
    CustomerNotFoundError,
    EventPublicationError,
)
from internal.application.usecases.authenticate_customer import AuthenticateCustomer
from internal.application.usecases.change_customer_status import (
    ActivateCustomer,
    DeactivateCustomer,
    ResolveCustomerSuspension,
    SuspendCustomer,
)
from internal.application.usecases.get_customer_by_id import GetCustomerById
from internal.application.usecases.list_customers import ListCustomers
from internal.application.usecases.register_customer import RegisterCustomer
from internal.application.usecases.update_customer_info import UpdateCustomerInfo
from internal.application.usecases.validate_customer_for_reservation import (
    ValidateCustomerForReservation,
)
from internal.domain.errors import DomainRuleViolation
from internal.infrastructure.auth.bcrypt_password_hasher import BcryptPasswordHasher
from internal.infrastructure.auth.jwt_token_generator import JWTTokenGenerator
from internal.infrastructure.config.settings import CustomerServiceSettings
from internal.infrastructure.messaging.factory import create_event_publisher
from internal.infrastructure.persistence.sqlalchemy_customer_repository import (
    SqlAlchemyCustomerRepository,
)
from internal.infrastructure.persistence.unit_of_work import create_session_factory
from internal.interfaces.rest.schemas import (
    AuthenticationResponse,
    ChangeStatusRequest,
    CustomerResponse,
    ErrorResponse,
    LoginRequest,
    RegisterCustomerRequest,
    ReservationEligibilityResponse,
    UpdateCustomerRequest,
)
from internal.interfaces.rest.security import require_admin_actor

API_TITLE = "Hotel DDD Customer Service API"
API_DESCRIPTION = (
    "REST API for customer registration, authentication, administrative "
    "customer management, and reservation eligibility queries."
)
API_VERSION = "0.1.0"
ALLOWED_CORS_ORIGINS = [
    "http://20.116.218.234:80",
    "http://localhost:5173",
]

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {
        "name": "Auth",
        "description": (
            "Public authentication endpoints for customer registration and login."
        ),
    },
    {
        "name": "Customers",
        "description": "Customer read endpoints and reservation eligibility queries.",
    },
    {
        "name": "Admin",
        "description": (
            "Administrative customer management endpoints protected by Bearer "
            "admin auth."
        ),
    },
    {
        "name": "Health",
        "description": "Operational health endpoint for runtime checks.",
    },
]

UNAUTHORIZED_RESPONSE = {
    "model": ErrorResponse,
    "description": "Missing or invalid Bearer token",
}
FORBIDDEN_RESPONSE = {
    "model": ErrorResponse,
    "description": "Authenticated actor does not have admin role",
}
NOT_FOUND_RESPONSE = {
    "model": ErrorResponse,
    "description": "Customer was not found",
}
INVALID_INPUT_RESPONSE = {
    "model": ErrorResponse,
    "description": "Invalid input payload",
}
DUPLICATE_CUSTOMER_RESPONSE = {
    "model": ErrorResponse,
    "description": "Customer email already exists",
}
CONFLICT_RESPONSE = {
    "model": ErrorResponse,
    "description": "Customer state transition conflicts with current status",
}
SERVICE_UNAVAILABLE_RESPONSE = {
    "model": ErrorResponse,
    "description": "Customer event publication failed",
}


def _handle_application_error(
    error: ApplicationError | DomainRuleViolation,
) -> JSONResponse:
    if isinstance(error, CustomerNotFoundError):
        return JSONResponse(status_code=404, content={"detail": "Customer not found"})
    if isinstance(error, CustomerAlreadyExistsError):
        return JSONResponse(
            status_code=409,
            content={"detail": "Customer with this email already exists"},
        )
    if isinstance(error, AuthenticationFailedError):
        return JSONResponse(status_code=401, content={"detail": str(error)})
    if isinstance(error, AuthorizationDeniedError):
        return JSONResponse(status_code=403, content={"detail": str(error)})
    if isinstance(error, EventPublicationError):
        return JSONResponse(
            status_code=503,
            content={"detail": "Customer event publication failed"},
        )
    if isinstance(error, DomainRuleViolation):
        return JSONResponse(status_code=409, content={"detail": str(error)})
    return JSONResponse(status_code=400, content={"detail": str(error)})


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request, error: ApplicationError
    ) -> JSONResponse:
        logger.warning(
            "Customer service request failed method=%s path=%s error_type=%s",
            request.method,
            request.url.path,
            error.__class__.__name__,
        )
        return _handle_application_error(error)

    @app.exception_handler(DomainRuleViolation)
    async def domain_rule_violation_handler(
        request: Request, error: DomainRuleViolation
    ) -> JSONResponse:
        logger.warning(
            "Customer domain rule violation method=%s path=%s error_type=%s",
            request.method,
            request.url.path,
            error.__class__.__name__,
        )
        return _handle_application_error(error)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request, error: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unexpected customer-service error method=%s path=%s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


def _log_auth_event(action: str, *, email: str) -> None:
    logger.info("Customer auth %s email=%s", action, email)


def _log_status_change(action: str, *, customer_id: str) -> None:
    logger.info("Customer status %s completed", action)


def _configure_logging() -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=logging.INFO)


def _verify_database_connection(session_factory: Any) -> None:
    engine = session_factory.kw["bind"]
    try:
        with engine.connect():
            return None
    except SQLAlchemyError as error:
        logger.exception("Customer service database connectivity check failed")
        raise RuntimeError("Customer service database is unreachable") from error


def create_app(settings: CustomerServiceSettings | None = None) -> FastAPI:
    _configure_logging()
    resolved_settings = settings or CustomerServiceSettings()
    session_factory = create_session_factory(resolved_settings.resolved_database_url)
    _verify_database_connection(session_factory)

    repository = SqlAlchemyCustomerRepository(session_factory)
    password_hasher = BcryptPasswordHasher()
    token_generator = JWTTokenGenerator(resolved_settings)
    event_publisher = create_event_publisher(resolved_settings)

    app = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=API_VERSION,
        openapi_tags=OPENAPI_TAGS,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _register_exception_handlers(app)
    app.state.session_factory = session_factory
    app.state.database_url = resolved_settings.resolved_database_url
    app.state.customer_repository = repository
    app.state.password_hasher = password_hasher
    app.state.token_generator = token_generator
    app.state.event_publisher = event_publisher

    admin_dependency = partial(require_admin_actor, token_generator)
    require_admin = Depends(admin_dependency)

    @app.post(
        "/auth/register",
        status_code=status.HTTP_201_CREATED,
        response_model=AuthenticationResponse,
        response_model_by_alias=True,
        tags=["Auth"],
        summary="Register a new customer",
        description=(
            "Creates a new customer account, issues a short-lived JWT, and returns "
            "the authenticated customer profile."
        ),
        responses={409: DUPLICATE_CUSTOMER_RESPONSE, 503: SERVICE_UNAVAILABLE_RESPONSE},
    )
    def register_customer(payload: RegisterCustomerRequest):
        _log_auth_event("register_attempt", email=str(payload.email))
        result = RegisterCustomer(
            app.state.customer_repository,
            app.state.password_hasher,
            app.state.token_generator,
            app.state.event_publisher,
        ).execute(
            RegisterCustomerCommand(
                name=payload.name,
                email=str(payload.email),
                phone=payload.phone,
                password=payload.password,
            )
        )
        _log_auth_event("register_succeeded", email=result.customer.email)
        return AuthenticationResponse.model_validate(result, from_attributes=True)

    @app.post(
        "/auth/login",
        response_model=AuthenticationResponse,
        response_model_by_alias=True,
        tags=["Auth"],
        summary="Authenticate customer",
        description=(
            "Authenticates an existing customer with email and password and returns "
            "a JWT Bearer token."
        ),
        responses={401: UNAUTHORIZED_RESPONSE},
    )
    def authenticate_customer(payload: LoginRequest):
        _log_auth_event("login_attempt", email=str(payload.email))
        result = AuthenticateCustomer(
            app.state.customer_repository,
            app.state.password_hasher,
            app.state.token_generator,
        ).execute(
            AuthenticateCustomerCommand(
                email=str(payload.email),
                password=payload.password,
            )
        )
        _log_auth_event("login_succeeded", email=result.customer.email)
        return AuthenticationResponse.model_validate(result, from_attributes=True)

    @app.get(
        "/customers/{customer_id}",
        response_model=CustomerResponse,
        response_model_by_alias=True,
        tags=["Customers"],
        summary="Get customer by identifier",
        description=(
            "Returns the current profile data for a customer by its identifier."
        ),
        responses={404: NOT_FOUND_RESPONSE},
    )
    def get_customer(customer_id: str):
        result = GetCustomerById(app.state.customer_repository).execute(customer_id)
        return CustomerResponse.model_validate(result, from_attributes=True)

    @app.get(
        "/customers/{customer_id}/reservation-eligibility",
        response_model=ReservationEligibilityResponse,
        response_model_by_alias=True,
        tags=["Customers"],
        summary="Check reservation eligibility",
        description=(
            "Evaluates whether the customer is currently eligible to create new "
            "reservations based on its lifecycle status."
        ),
        responses={404: NOT_FOUND_RESPONSE},
    )
    def validate_customer_for_reservation(customer_id: str):
        result = ValidateCustomerForReservation(app.state.customer_repository).execute(
            customer_id
        )
        return ReservationEligibilityResponse.model_validate(
            result, from_attributes=True
        )

    @app.patch(
        "/customers/{customer_id}",
        response_model=CustomerResponse,
        response_model_by_alias=True,
        tags=["Admin"],
        summary="Update customer profile",
        description=(
            "Updates mutable customer data. Requires a valid Bearer token with the "
            "admin role."
        ),
        responses={
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: NOT_FOUND_RESPONSE,
            503: SERVICE_UNAVAILABLE_RESPONSE,
        },
    )
    def update_customer(
        customer_id: str,
        payload: UpdateCustomerRequest,
        _actor=require_admin,
    ):
        result = UpdateCustomerInfo(
            app.state.customer_repository, app.state.event_publisher
        ).execute(
            UpdateCustomerInfoCommand(
                customer_id=customer_id,
                name=payload.name,
                phone=payload.phone,
            )
        )
        return CustomerResponse.model_validate(result, from_attributes=True)

    @app.patch(
        "/customers/{customer_id}/deactivate",
        response_model=CustomerResponse,
        response_model_by_alias=True,
        tags=["Admin"],
        summary="Deactivate customer",
        description=(
            "Transitions an active customer to INACTIVE status. Requires Bearer "
            "admin authentication."
        ),
        responses={
            409: CONFLICT_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: NOT_FOUND_RESPONSE,
            503: SERVICE_UNAVAILABLE_RESPONSE,
        },
    )
    def deactivate_customer(
        customer_id: str,
        payload: ChangeStatusRequest,
        _actor=require_admin,
    ):
        result = DeactivateCustomer(
            app.state.customer_repository, app.state.event_publisher
        ).execute(
            DeactivateCustomerCommand(customer_id=customer_id, reason=payload.reason)
        )
        _log_status_change("deactivate", customer_id=customer_id)
        return CustomerResponse.model_validate(result, from_attributes=True)

    @app.patch(
        "/customers/{customer_id}/activate",
        response_model=CustomerResponse,
        response_model_by_alias=True,
        tags=["Admin"],
        summary="Activate customer",
        description=(
            "Transitions an inactive customer back to ACTIVE status. Requires Bearer "
            "admin authentication."
        ),
        responses={
            409: CONFLICT_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: NOT_FOUND_RESPONSE,
            503: SERVICE_UNAVAILABLE_RESPONSE,
        },
    )
    def activate_customer(customer_id: str, _actor=require_admin):
        result = ActivateCustomer(
            app.state.customer_repository, app.state.event_publisher
        ).execute(ActivateCustomerCommand(customer_id=customer_id))
        _log_status_change("activate", customer_id=customer_id)
        return CustomerResponse.model_validate(result, from_attributes=True)

    @app.patch(
        "/customers/{customer_id}/suspend",
        response_model=CustomerResponse,
        response_model_by_alias=True,
        tags=["Admin"],
        summary="Suspend customer",
        description=(
            "Transitions an active customer to SUSPENDED status. Requires Bearer "
            "admin authentication."
        ),
        responses={
            409: CONFLICT_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: NOT_FOUND_RESPONSE,
            503: SERVICE_UNAVAILABLE_RESPONSE,
        },
    )
    def suspend_customer(
        customer_id: str,
        payload: ChangeStatusRequest,
        _actor=require_admin,
    ):
        result = SuspendCustomer(
            app.state.customer_repository, app.state.event_publisher
        ).execute(
            SuspendCustomerCommand(customer_id=customer_id, reason=payload.reason)
        )
        _log_status_change("suspend", customer_id=customer_id)
        return CustomerResponse.model_validate(result, from_attributes=True)

    @app.patch(
        "/customers/{customer_id}/resolve-suspension",
        response_model=CustomerResponse,
        response_model_by_alias=True,
        tags=["Admin"],
        summary="Resolve customer suspension",
        description=(
            "Transitions a suspended customer back to ACTIVE status. Requires Bearer "
            "admin authentication."
        ),
        responses={
            409: CONFLICT_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: NOT_FOUND_RESPONSE,
            503: SERVICE_UNAVAILABLE_RESPONSE,
        },
    )
    def resolve_customer_suspension(customer_id: str, _actor=require_admin):
        result = ResolveCustomerSuspension(
            app.state.customer_repository, app.state.event_publisher
        ).execute(ResolveCustomerSuspensionCommand(customer_id=customer_id))
        _log_status_change("resolve_suspension", customer_id=customer_id)
        return CustomerResponse.model_validate(result, from_attributes=True)

    @app.get(
        "/customers",
        response_model=list[CustomerResponse],
        response_model_by_alias=True,
        tags=["Admin"],
        summary="List customers",
        description=(
            "Returns the registered customers visible to administrative operators. "
            "Requires Bearer admin authentication."
        ),
        responses={401: UNAUTHORIZED_RESPONSE, 403: FORBIDDEN_RESPONSE},
    )
    def list_customers(_actor=require_admin):
        result = ListCustomers(app.state.customer_repository).execute()
        return [
            CustomerResponse.model_validate(item, from_attributes=True)
            for item in result
        ]

    @app.get(
        "/health",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Health"],
        summary="Health check",
        description="Returns 204 when the service is up and able to serve requests.",
    )
    def health() -> Response:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app
