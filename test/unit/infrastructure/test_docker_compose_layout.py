from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_When_ReadingBaseCompose_Expect_DeployReadyAppOnlyDefinition() -> None:
    # Arrange
    compose_content = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    # Act
    base_has_mysql_service = "\n  mysql:" in compose_content
    base_has_rabbitmq_service = "\n  rabbitmq:" in compose_content

    # Assert
    assert "\n  customer-service:" in compose_content
    assert not base_has_mysql_service
    assert not base_has_rabbitmq_service
    assert "CUSTOMER_SERVICE_JWT_SECRET:" in compose_content
    assert "CUSTOMER_SERVICE_DATABASE_URL:" in compose_content
    assert "CUSTOMER_SERVICE_RABBITMQ_URL:" in compose_content
    assert "image: ${CUSTOMER_SERVICE_IMAGE:-customer-service:latest}" in compose_content
    assert "build:" in compose_content
    assert "depends_on:" not in compose_content
    assert "healthcheck:" in compose_content
    assert "restart: unless-stopped" in compose_content
    assert "${CUSTOMER_SERVICE_PORT:-8000}:8000" in compose_content
    assert "./data:/app/data" not in compose_content


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
    assert "MYSQL_DATABASE: ${MYSQL_DATABASE:-customer_service}" in compose_content
    assert "MYSQL_USER: ${MYSQL_USER:-customer_app}" in compose_content
    assert "MYSQL_PASSWORD: ${MYSQL_PASSWORD:-customer_app_local}" in compose_content
    assert "MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-root_local}" in compose_content
    assert "MYSQL_LOCAL_PORT: ${MYSQL_LOCAL_PORT:-3306}" in compose_content
    assert (
        "RABBITMQ_DEFAULT_USER: ${RABBITMQ_DEFAULT_USER:-guest}" in compose_content
    )
    assert (
        "RABBITMQ_DEFAULT_PASS: ${RABBITMQ_DEFAULT_PASS:-guest}" in compose_content
    )
    assert "RABBITMQ_PORT: ${RABBITMQ_PORT:-5672}" in compose_content
    assert "${RABBITMQ_UI_PORT:-15672}:15672" in compose_content
    assert "${CUSTOMER_SERVICE_JWT_SECRET:-local-dev-secret}" in compose_content
    assert "${CUSTOMER_SERVICE_PORT:-8000}:8000" in compose_content
    assert "${MYSQL_LOCAL_PORT:-3306}:3306" in compose_content
    assert "${RABBITMQ_PORT:-5672}:5672" in compose_content


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


def test_When_ReadingDeployDockerDocs_Expect_BaseComposeDeployCommandDocumented() -> None:
    # Arrange
    readme_content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    service_doc_content = (
        REPO_ROOT / "docs" / "services" / "customer-service.md"
    ).read_text(encoding="utf-8")

    # Assert
    expected_deploy_command = (
        "docker compose --env-file .env.deploy -f docker-compose.yml up -d"
    )
    assert expected_deploy_command in readme_content
    assert expected_deploy_command in service_doc_content
