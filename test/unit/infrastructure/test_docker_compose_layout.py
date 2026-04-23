from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_When_ReadingBaseCompose_Expect_OnlyCustomerServiceAppDefinition() -> None:
    # Arrange
    compose_content = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    # Act
    base_has_mysql_service = "\n  mysql:" in compose_content
    base_has_rabbitmq_service = "\n  rabbitmq:" in compose_content

    # Assert
    assert "\n  customer-service:" in compose_content
    assert not base_has_mysql_service
    assert not base_has_rabbitmq_service
    assert "CUSTOMER_SERVICE_DATABASE_URL" not in compose_content
    assert "CUSTOMER_SERVICE_RABBITMQ_URL" not in compose_content
    assert "depends_on:" not in compose_content
    assert '"8000:8000"' not in compose_content


def test_When_ReadingDevCompose_Expect_LocalInfrastructureAndOverridesPresent() -> None:
    # Arrange
    dev_compose_path = REPO_ROOT / "docker-compose.dev.yml"

    # Act
    compose_content = dev_compose_path.read_text(encoding="utf-8")

    # Assert
    assert "\n  customer-service:" in compose_content
    assert "\n  mysql:" in compose_content
    assert "\n  rabbitmq:" in compose_content
    assert "depends_on:" in compose_content
    assert "condition: service_healthy" in compose_content
    assert (
        "CUSTOMER_SERVICE_DATABASE_URL: mysql+pymysql://customer_app:customer_app_secret@mysql:3306/customer_service?charset=utf8mb4"
        in compose_content
    )
    assert (
        "CUSTOMER_SERVICE_RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/%2F"
        in compose_content
    )
    assert '"8000:8000"' in compose_content
    assert '"3306:3306"' in compose_content
    assert '"5672:5672"' in compose_content
    assert '"15672:15672"' in compose_content


def test_When_ReadingLocalDockerDocs_Expect_CombinedComposeCommandDocumented() -> None:
    # Arrange
    readme_content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    service_doc_content = (
        REPO_ROOT / "docs" / "services" / "customer-service.md"
    ).read_text(encoding="utf-8")

    # Act
    expected_command = (
        "docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d"
    )

    # Assert
    assert expected_command in readme_content
    assert expected_command in service_doc_content
    assert "docker-compose.dev.yml" in readme_content
    assert "docker-compose.dev.yml" in service_doc_content
