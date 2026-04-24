import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from internal.application.commands.register_customer import RegisterCustomerCommand
from internal.application.usecases.register_customer import RegisterCustomer
from internal.domain.entities.customer import Customer
from internal.domain.valueobjects.customer_role import CustomerRole
from internal.domain.valueobjects.customer_status import CustomerStatus
from internal.domain.valueobjects.email import Email
from internal.infrastructure.auth.bcrypt_password_hasher import BcryptPasswordHasher
from internal.infrastructure.config.settings import CustomerServiceSettings
from internal.infrastructure.persistence.sqlalchemy_customer_repository import (
    SqlAlchemyCustomerRepository,
)
from internal.infrastructure.persistence.unit_of_work import create_session_factory
from internal.interfaces.rest.app import create_app


def test_When_CustomerIsPersisted_Expect_RepositoryRoundTripPreservesAggregateData(  # noqa: E501
    mysql_customer_runtime,
) -> None:
    # Arrange
    session_factory = create_session_factory(mysql_customer_runtime.database_url)
    repository = SqlAlchemyCustomerRepository(session_factory)
    customer = Customer.register(
        customer_id=uuid4(),
        name="Jane Doe",
        email=Email("jane@example.com"),
        phone="+57-3000000000",
        password_hash="hashed::plain-password",
        registered_at=datetime(2026, 4, 21, tzinfo=UTC),
    )

    # Act
    repository.add(customer)
    loaded_customer = repository.get_by_id(customer.customer_id)

    # Assert
    assert loaded_customer is not None
    assert loaded_customer.customer_id == customer.customer_id
    assert loaded_customer.email.value == "jane@example.com"
    assert loaded_customer.status is CustomerStatus.ACTIVE


def test_When_CustomerEmailAlreadyExists_Expect_RepositoryRejectsDuplicateEmail(
    mysql_customer_runtime,
) -> None:
    # Arrange
    session_factory = create_session_factory(mysql_customer_runtime.database_url)
    repository = SqlAlchemyCustomerRepository(session_factory)
    first_customer = Customer.register(
        customer_id=uuid4(),
        name="Jane Doe",
        email=Email("jane@example.com"),
        phone="+57-3000000000",
        password_hash="hashed::plain-password",
        registered_at=datetime(2026, 4, 21, tzinfo=UTC),
    )
    duplicate_customer = Customer.register(
        customer_id=uuid4(),
        name="Jane Roe",
        email=Email("jane@example.com"),
        phone="+57-3111111111",
        password_hash="hashed::other-password",
        registered_at=datetime(2026, 4, 22, tzinfo=UTC),
    )
    repository.add(first_customer)

    # Act / Assert
    with pytest.raises(ValueError, match="already exists"):
        repository.add(duplicate_customer)


def test_When_RegisteringAndLoggingInThroughApi_Expect_AuthResponsesWithoutPasswordHash(  # noqa: E501
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)

    # Act
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "+57-3000000000",
            "password": "plain-password",
        },
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "jane@example.com", "password": "plain-password"},
    )

    # Assert
    assert register_response.status_code == 201
    assert register_response.json()["customer"]["email"] == "jane@example.com"
    assert "passwordHash" not in register_response.json()["customer"]
    assert login_response.status_code == 200
    assert login_response.json()["customer"]["status"] == "ACTIVE"
    assert "passwordHash" not in login_response.json()["customer"]


def test_When_CustomerIsInactive_Expect_ReservationEligibilityEndpointReturnsFalse(  # noqa: E501
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(
        mysql_customer_runtime_factory,
        seed_customer_status=CustomerStatus.INACTIVE,
    )
    client = TestClient(app)
    customer_id = app.state.seed_customer_id

    # Act
    response = client.get(f"/customers/{customer_id}/reservation-eligibility")

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "customerId": customer_id,
        "status": "INACTIVE",
        "isEligible": False,
    }


def test_When_AdminResolvesSuspension_Expect_CustomerReturnsToActive(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(
        mysql_customer_runtime_factory,
        seed_customer_status=CustomerStatus.SUSPENDED,
    )
    client = TestClient(app)
    customer_id = app.state.seed_customer_id
    admin_token = app.state.admin_token

    # Act
    response = client.patch(
        f"/customers/{customer_id}/resolve-suspension",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_When_UpdatingCustomerWithoutBearerToken_Expect_Unauthorized(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)
    customer_id = app.state.seed_customer_id

    # Act
    response = client.patch(
        f"/customers/{customer_id}",
        json={"name": "Jane Admin Update"},
    )

    # Assert
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token"}


def test_When_UpdatingCustomerWithNonAdminRole_Expect_Forbidden(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)
    customer_id = app.state.seed_customer_id
    customer_token = app.state.customer_token

    # Act
    response = client.patch(
        f"/customers/{customer_id}",
        json={"name": "Jane Customer Update"},
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    # Assert
    assert response.status_code == 403
    assert response.json() == {"detail": "Admin role is required"}


def test_When_AdminUpdatesCustomer_Expect_CustomerInfoUpdated(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)
    customer_id = app.state.seed_customer_id
    admin_token = app.state.admin_token

    # Act
    response = client.patch(
        f"/customers/{customer_id}",
        json={"name": "Jane Admin Update", "phone": "+57-3222222222"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "customerId": customer_id,
        "name": "Jane Admin Update",
        "email": "seed@example.com",
        "phone": "+57-3222222222",
        "status": "ACTIVE",
        "role": "customer",
    }


def test_When_RegisteringDuplicateEmail_Expect_BadRequest(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)

    client.post(
        "/auth/register",
        json={
            "name": "Jane Doe",
            "email": "duplicate@example.com",
            "phone": "+57-3000000000",
            "password": "plain-password",
        },
    )

    # Act
    response = client.post(
        "/auth/register",
        json={
            "name": "Jane Roe",
            "email": "duplicate@example.com",
            "phone": "+57-3111111111",
            "password": "plain-password",
        },
    )

    # Assert
    assert response.status_code == 409
    assert response.json() == {"detail": "Customer with this email already exists"}


def test_When_AuthenticatingWithInvalidPassword_Expect_BadRequest(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)

    # Act
    response = client.post(
        "/auth/login",
        json={"email": "seed@example.com", "password": "wrong-password"},
    )

    # Assert
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_When_AdminSuspendsInactiveCustomer_Expect_ConflictResponse(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(
        mysql_customer_runtime_factory,
        seed_customer_status=CustomerStatus.INACTIVE,
    )
    client = TestClient(app)
    customer_id = app.state.seed_customer_id
    admin_token = app.state.admin_token

    # Act
    response = client.patch(
        f"/customers/{customer_id}/suspend",
        json={"reason": "policy_violation"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Assert
    assert response.status_code == 409
    assert response.json() == {"detail": "Cannot suspend a customer that is not active"}


def test_When_AdminUsesInvalidBearerToken_Expect_UnauthorizedResponse(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)
    customer_id = app.state.seed_customer_id

    # Act
    response = client.patch(
        f"/customers/{customer_id}",
        json={"name": "Jane Admin Update"},
        headers={"Authorization": "Bearer invalid-token"},
    )

    # Assert
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid bearer token"}


def test_When_EventPublicationFailsDuringRegistration_Expect_ServiceUnavailable(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    app.state.event_publisher = FailingEventPublisher()
    client = TestClient(app)

    # Act
    response = client.post(
        "/auth/register",
        json={
            "name": "Jane Doe",
            "email": "publish-failure@example.com",
            "phone": "+57-3000000000",
            "password": "plain-password",
        },
    )

    # Assert
    assert response.status_code == 503
    assert response.json() == {"detail": "Customer event publication failed"}


def test_When_RegisteringCustomer_Expect_AuthAttemptAndSuccessAreLogged(
    mysql_customer_runtime_factory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    caplog.set_level(logging.INFO)
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)

    # Act
    response = client.post(
        "/auth/register",
        json={
            "name": "Jane Doe",
            "email": "logged-register@example.com",
            "phone": "+57-3000000000",
            "password": "plain-password",
        },
    )

    # Assert
    assert response.status_code == 201
    assert (
        "Customer auth register_attempt email=logged-register@example.com"
        in caplog.text
    )
    assert (
        "Customer auth register_succeeded email=logged-register@example.com"
        in caplog.text
    )
    assert "plain-password" not in caplog.text


def test_When_LoggingInCustomer_Expect_AuthAttemptAndSuccessAreLogged(
    mysql_customer_runtime_factory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    caplog.set_level(logging.INFO)
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)

    # Act
    response = client.post(
        "/auth/login",
        json={"email": "seed@example.com", "password": "plain-password"},
    )

    # Assert
    assert response.status_code == 200
    assert "Customer auth login_attempt email=seed@example.com" in caplog.text
    assert "Customer auth login_succeeded email=seed@example.com" in caplog.text
    assert "plain-password" not in caplog.text


def test_When_AdminSuspendsCustomer_Expect_StatusChangeIsLogged(
    mysql_customer_runtime_factory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    caplog.set_level(logging.INFO)
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)
    customer_id = app.state.seed_customer_id
    admin_token = app.state.admin_token

    # Act
    response = client.patch(
        f"/customers/{customer_id}/suspend",
        json={"reason": "policy_violation"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Assert
    assert response.status_code == 200
    assert "Customer status suspend completed" in caplog.text


def test_When_UnexpectedErrorOccurs_Expect_InternalServerErrorAndExceptionLogged(
    mysql_customer_runtime_factory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    caplog.set_level(logging.ERROR)
    app = _build_app(mysql_customer_runtime_factory)
    app.state.customer_repository = ExplodingCustomerRepository()
    client = TestClient(app, raise_server_exceptions=False)

    # Act
    response = client.get(f"/customers/{uuid4()}")

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert (
        "Unexpected customer-service error method=GET path=/customers/" in caplog.text
    )


def test_When_RequestingUnknownCustomer_Expect_NotFoundResponse(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)

    # Act
    response = client.get(f"/customers/{uuid4()}")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}


def test_When_CheckingUnknownCustomerEligibility_Expect_NotFoundResponse(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)

    # Act
    response = client.get(f"/customers/{uuid4()}/reservation-eligibility")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}


def test_When_UpdatingUnknownCustomer_Expect_NotFoundResponse(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)
    admin_token = app.state.admin_token

    # Act
    response = client.patch(
        f"/customers/{uuid4()}",
        json={"name": "Unknown Customer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}


def test_When_AdminDeactivatesActiveCustomer_Expect_CustomerBecomesInactive(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)
    customer_id = app.state.seed_customer_id
    admin_token = app.state.admin_token

    # Act
    response = client.patch(
        f"/customers/{customer_id}/deactivate",
        json={"reason": "manual"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"


def test_When_AdminActivatesInactiveCustomer_Expect_CustomerBecomesActive(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(
        mysql_customer_runtime_factory,
        seed_customer_status=CustomerStatus.INACTIVE,
    )
    client = TestClient(app)
    customer_id = app.state.seed_customer_id
    admin_token = app.state.admin_token

    # Act
    response = client.patch(
        f"/customers/{customer_id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_When_AdminSuspendsActiveCustomer_Expect_CustomerBecomesSuspended(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)
    customer_id = app.state.seed_customer_id
    admin_token = app.state.admin_token

    # Act
    response = client.patch(
        f"/customers/{customer_id}/suspend",
        json={"reason": "policy_violation"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "SUSPENDED"


def test_When_AdminListsCustomers_Expect_RegisteredCustomersReturned(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)
    admin_token = app.state.admin_token

    # Act
    response = client.get(
        "/customers",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == [
        {
            "customerId": app.state.seed_customer_id,
            "name": "Seed Customer",
            "email": "seed@example.com",
            "phone": "+57-3999999999",
            "status": "ACTIVE",
            "role": "customer",
        }
    ]


def test_When_HealthEndpointIsCalled_Expect_NoContent(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 204
    assert response.content == b""


def test_When_RequestingOpenApiSchema_Expect_GlobalMetadataAndTaggedEndpointDocumentation(  # noqa: E501
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)

    # Act
    response = client.get("/openapi.json")
    schema = response.json()
    register_operation = schema["paths"]["/auth/register"]["post"]
    admin_update_operation = schema["paths"]["/customers/{customer_id}"]["patch"]
    health_operation = schema["paths"]["/health"]["get"]

    # Assert
    assert response.status_code == 200
    assert schema["info"] == {
        "title": "Hotel DDD Customer Service API",
        "description": (
            "REST API for customer registration, authentication, administrative "
            "customer management, and reservation eligibility queries."
        ),
        "version": "0.1.0",
    }
    assert [tag["name"] for tag in schema["tags"]] == [
        "Auth",
        "Customers",
        "Admin",
        "Health",
    ]
    assert register_operation["tags"] == ["Auth"]
    assert register_operation["summary"] == "Register a new customer"
    assert "customer account" in register_operation["description"]
    assert (
        register_operation["responses"]["409"]["description"]
        == "Customer email already exists"
    )
    assert admin_update_operation["tags"] == ["Admin"]
    assert admin_update_operation["summary"] == "Update customer profile"
    assert (
        admin_update_operation["responses"]["401"]["description"]
        == "Missing or invalid Bearer token"
    )
    assert (
        admin_update_operation["responses"]["403"]["description"]
        == "Authenticated actor does not have admin role"
    )
    assert (
        admin_update_operation["responses"]["404"]["description"]
        == "Customer was not found"
    )
    assert health_operation["tags"] == ["Health"]
    assert health_operation["summary"] == "Health check"


def test_When_RequestingOpenApiSchema_Expect_BearerSecurityAndSchemaExamplesDocumented(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange
    app = _build_app(mysql_customer_runtime_factory)
    client = TestClient(app)

    # Act
    response = client.get("/openapi.json")
    schema = response.json()
    security_scheme = schema["components"]["securitySchemes"]["HTTPBearer"]
    admin_update_operation = schema["paths"]["/customers/{customer_id}"]["patch"]
    register_request_schema = schema["components"]["schemas"]["RegisterCustomerRequest"]
    change_status_schema = schema["components"]["schemas"]["ChangeStatusRequest"]
    auth_response_schema = schema["components"]["schemas"]["AuthenticationResponse"]

    # Assert
    assert response.status_code == 200
    assert security_scheme == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Paste a Bearer token to access admin endpoints.",
    }
    assert admin_update_operation["security"] == [{"HTTPBearer": []}]
    assert (
        register_request_schema["properties"]["name"]["description"]
        == "Customer full name"
    )
    assert (
        register_request_schema["properties"]["password"]["description"]
        == "Plain password used only during registration or login"
    )
    assert register_request_schema["properties"]["email"]["examples"] == [
        "jane@example.com"
    ]
    assert change_status_schema["properties"]["reason"]["examples"] == ["manual_review"]
    assert (
        auth_response_schema["properties"]["accessToken"]["description"]
        == "JWT access token for authenticated requests"
    )


def test_When_BuildingIntegrationApps_Expect_IsolatedMySqlDatabasePerApp(
    mysql_customer_runtime_factory,
) -> None:
    # Arrange / Act
    first_app = _build_app(mysql_customer_runtime_factory)
    second_app = _build_app(mysql_customer_runtime_factory)

    # Assert
    assert first_app.state.database_url != second_app.state.database_url
    assert first_app.state.database_url.startswith("mysql+pymysql://")
    assert second_app.state.database_url.startswith("mysql+pymysql://")


def test_When_RunningAlembicAgainstCustomerSchema_Expect_OnlyCustomerTables(
    mysql_customer_runtime,
) -> None:
    # Arrange
    engine = create_session_factory(mysql_customer_runtime.database_url).kw["bind"]

    # Act
    with engine.connect() as connection:
        tables = (
            connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() ORDER BY table_name"
                )
            )
            .scalars()
            .all()
        )
        customer_table = connection.execute(
            text(
                "SELECT table_collation FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = 'customers'"
            )
        ).scalar_one()
        database_collation = connection.execute(
            text("SELECT @@collation_database")
        ).scalar_one()
        database_charset = connection.execute(
            text("SELECT @@character_set_database")
        ).scalar_one()

    # Assert
    assert tables == ["customer_alembic_version", "customers"]
    assert customer_table == "utf8mb4_0900_ai_ci"
    assert database_collation == "utf8mb4_0900_ai_ci"
    assert database_charset == "utf8mb4"


def _build_app(
    mysql_customer_runtime_factory,
    seed_customer_status: CustomerStatus = CustomerStatus.ACTIVE,
) -> object:
    runtime = mysql_customer_runtime_factory()
    database_url = runtime.database_url

    settings = CustomerServiceSettings(
        database_url=database_url,
        jwt_secret="super-secret-key-with-32-chars-min",
        jwt_expiration_seconds=1800,
        event_publisher_backend="in-memory",
    )
    app = create_app(settings)
    app.state.database_url = database_url

    if seed_customer_status is not CustomerStatus.ACTIVE:
        session_factory = app.state.session_factory
        repository = SqlAlchemyCustomerRepository(session_factory)
        customer = Customer(
            customer_id=uuid4(),
            name="Seed Customer",
            email=Email("seed@example.com"),
            phone="+57-3999999999",
            password_hash=BcryptPasswordHasher().hash("plain-password"),
            status=seed_customer_status,
            role=CustomerRole.CUSTOMER,
            registered_at=datetime.now(UTC),
        )
        repository.add(customer)
        app.state.seed_customer_id = str(customer.customer_id)
    else:
        register_use_case = RegisterCustomer(
            app.state.customer_repository,
            app.state.password_hasher,
            app.state.token_generator,
            app.state.event_publisher,
        )
        result = register_use_case.execute(
            RegisterCustomerCommand(
                name="Seed Customer",
                email="seed@example.com",
                phone="+57-3999999999",
                password="plain-password",
            )
        )
        app.state.seed_customer_id = result.customer.customer_id

    app.state.admin_token = app.state.token_generator.generate(
        customer_id=str(uuid4()), role="admin"
    )
    app.state.customer_token = app.state.token_generator.generate(
        customer_id=app.state.seed_customer_id, role="customer"
    )
    return app


class FailingEventPublisher:
    def publish(self, event: object) -> None:
        raise RuntimeError("broker unavailable")


class ExplodingCustomerRepository:
    def get_by_id(self, customer_id: object) -> None:
        raise RuntimeError("database offline")
