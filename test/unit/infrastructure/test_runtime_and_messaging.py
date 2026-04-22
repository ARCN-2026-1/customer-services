from pathlib import Path


def test_When_RuntimeLayerExists_Expect_InfrastructureTestFoundationPresent() -> None:
    # Arrange
    root_dir = Path(__file__).resolve().parents[3]

    # Act / Assert
    assert (root_dir / "test" / "unit" / "infrastructure").exists()
