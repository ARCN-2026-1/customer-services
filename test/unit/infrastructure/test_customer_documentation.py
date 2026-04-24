from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_When_ReadingCustomerDocs_Expect_KeyNavigationLinksPresent() -> None:
    # Arrange
    readme_content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    # Act
    expected_links = [
        "docs/services/customer-service.md",
        "docs/services/integration-map.md",
        "docs/service-overview.md",
        "docs/ddd/customer-context.md",
    ]

    # Assert
    for link in expected_links:
        assert link in readme_content


def test_When_ReadingCustomerServiceDocs_Expect_MySqlAndDiagramsDocumented() -> None:
    # Arrange
    service_doc = (REPO_ROOT / "docs" / "services" / "customer-service.md").read_text(
        encoding="utf-8"
    )
    integration_map = (
        REPO_ROOT / "docs" / "services" / "integration-map.md"
    ).read_text(encoding="utf-8")

    # Act
    service_has_status_diagram = "stateDiagram-v2" in service_doc
    service_has_layer_diagram = "Interfaces\\nREST API" in service_doc

    # Assert
    assert "adaptador de persistencia MySQL" in service_doc
    assert "usa MySQL con schema dedicado" in integration_map
    assert "SQLite" not in integration_map
    assert service_has_status_diagram
    assert service_has_layer_diagram


def test_When_ReadingCustomerContextDoc_Expect_CurrentMvpModelAndEvents() -> None:
    # Arrange
    customer_context = (REPO_ROOT / "docs" / "ddd" / "customer-context.md").read_text(
        encoding="utf-8"
    )

    # Assert
    assert "AuthenticateCustomer" in customer_context
    assert "ListCustomers" in customer_context
    assert "CustomerActivated" in customer_context
    assert "CustomerSuspensionResolved" in customer_context
    assert "passwordHash" in customer_context
    assert "role" in customer_context
