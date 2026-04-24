from __future__ import annotations

from pathlib import Path

import pytest

from alembic.config import Config
from internal.infrastructure.config.settings import (
    ALEMBIC_INI_DEFAULT_DATABASE_URL,
    escape_for_alembic_config,
    resolve_alembic_database_url,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_When_AlembicIniUrlIsDefaultPlaceholder_Expect_RuntimeDatabaseUrlWins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.delenv("CUSTOMER_SERVICE_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CUSTOMER_SERVICE_DB_HOST", "mysql.prod.internal")
    monkeypatch.setenv("CUSTOMER_SERVICE_DB_PORT", "3310")
    monkeypatch.setenv("CUSTOMER_SERVICE_DB_NAME", "customer_prod")
    monkeypatch.setenv("CUSTOMER_SERVICE_DB_USER", "runtime_user")
    monkeypatch.setenv("CUSTOMER_SERVICE_DB_PASSWORD", "runtime_secret")

    # Act
    resolved_url = resolve_alembic_database_url(ALEMBIC_INI_DEFAULT_DATABASE_URL)

    # Assert
    assert (
        resolved_url
        == "mysql+pymysql://runtime_user:runtime_secret@mysql.prod.internal:3310/customer_prod?charset=utf8mb4"
    )


def test_When_AlembicGetsExplicitSqlalchemyUrl_Expect_ItIsPreserved() -> None:
    # Arrange
    explicit_url = "mysql+pymysql://custom_user:custom_pass@db.example:3306/custom_db"

    # Act
    resolved_url = resolve_alembic_database_url(explicit_url)

    # Assert
    assert resolved_url == explicit_url


def test_When_SetMainOptionGetsPercentEncodedUrl_Expect_InterpolationFails() -> None:
    # Arrange
    config = Config()
    runtime_url = (
        "mysql+pymysql://runtime_user:Gh4%3A%23p%40ss@db.example:3306/"
        "customer_prod?charset=utf8mb4"
    )

    # Act / Assert
    with pytest.raises(ValueError, match="invalid interpolation syntax"):
        config.set_main_option("sqlalchemy.url", runtime_url)


def test_When_UsingEscapedUrlInAlembicConfig_Expect_PercentEncodedUrlRoundTrips() -> (
    None
):
    # Arrange
    config = Config()
    runtime_url = (
        "mysql+pymysql://runtime_user:Gh4%3A%23p%40ss@db.example:3306/"
        "customer_prod?charset=utf8mb4"
    )

    # Act
    config.set_main_option("sqlalchemy.url", escape_for_alembic_config(runtime_url))

    # Assert
    assert config.get_main_option("sqlalchemy.url") == runtime_url


def test_When_ReadingAlembicEnv_Expect_ServiceScopedVersionTableConfigured() -> None:
    # Arrange
    env_content = (REPO_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    # Assert
    assert 'ALEMBIC_VERSION_TABLE = "customer_alembic_version"' in env_content
    assert env_content.count("version_table=ALEMBIC_VERSION_TABLE") == 2
