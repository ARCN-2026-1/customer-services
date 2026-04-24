import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from testcontainers.mysql import MySqlContainer

from alembic import command
from alembic.config import Config

ROOT_DIR = Path(__file__).resolve().parents[1]
MYSQL_CHARSET = "utf8mb4"
MYSQL_COLLATION = "utf8mb4_0900_ai_ci"
MYSQL_IMAGE = "mysql:8.4"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@dataclass(frozen=True, slots=True)
class MySqlCustomerRuntime:
    database_url: str
    database_name: str
    db_user: str
    db_password: str


@dataclass(frozen=True, slots=True)
class MySqlAdminRuntime:
    host: str
    port: int
    root_password: str

    @property
    def root_database_url(self) -> str:
        return _build_mysql_url(
            host=self.host,
            port=self.port,
            database_name="mysql",
            db_user="root",
            db_password=self.root_password,
        )


def _build_mysql_url(
    *,
    host: str,
    port: int,
    database_name: str,
    db_user: str,
    db_password: str,
) -> str:
    return (
        "mysql+pymysql://"
        f"{db_user}:{db_password}@{host}:{port}/{database_name}"
        f"?charset={MYSQL_CHARSET}"
    )


def _build_alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["skip_logging_config"] = True
    return config


def _run_alembic_upgrade(database_url: str) -> None:
    command.upgrade(_build_alembic_config(database_url), "head")


def _provision_customer_database(
    admin_engine: Engine,
    *,
    database_name: str,
    db_user: str,
    db_password: str,
) -> None:
    with admin_engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE DATABASE `{database_name}` "
                f"CHARACTER SET {MYSQL_CHARSET} COLLATE {MYSQL_COLLATION}"
            )
        )
        connection.execute(
            text(f"CREATE USER '{db_user}'@'%' IDENTIFIED BY '{db_password}'")
        )
        connection.execute(
            text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX "
                f"ON `{database_name}`.* TO '{db_user}'@'%'"
            )
        )
        connection.execute(text("FLUSH PRIVILEGES"))


def _drop_customer_database(
    admin_engine: Engine, runtime: MySqlCustomerRuntime
) -> None:
    with admin_engine.begin() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS `{runtime.database_name}`"))
        connection.execute(text(f"DROP USER IF EXISTS '{runtime.db_user}'@'%'"))
        connection.execute(text("FLUSH PRIVILEGES"))


def _require_docker_daemon() -> None:
    try:
        import docker

        client = docker.from_env()
        client.ping()
        client.close()
    except Exception as error:  # pragma: no cover - environment guard
        pytest.skip(
            "Docker daemon unavailable; MySQL integration tests require Docker. "
            f"Original error: {error}"
        )


@pytest.fixture(scope="session")
def mysql_admin_runtime() -> MySqlAdminRuntime:
    _require_docker_daemon()
    with MySqlContainer(
        MYSQL_IMAGE,
        dialect="pymysql",
        username="root",
        password="root",
        dbname="mysql",
    ) as container:
        yield MySqlAdminRuntime(
            host=container.get_container_host_ip(),
            port=int(container.get_exposed_port(3306)),
            root_password="root",
        )


@pytest.fixture(scope="session")
def mysql_admin_engine(mysql_admin_runtime: MySqlAdminRuntime) -> Engine:
    engine = create_engine(mysql_admin_runtime.root_database_url, pool_pre_ping=True)
    try:
        with engine.connect():
            yield engine
    finally:
        engine.dispose()


@pytest.fixture
def mysql_customer_runtime_factory(
    mysql_admin_runtime: MySqlAdminRuntime,
    mysql_admin_engine: Engine,
):
    runtimes: list[MySqlCustomerRuntime] = []

    def factory() -> MySqlCustomerRuntime:
        suffix = uuid4().hex[:12]
        database_name = f"customer_service_{suffix}"
        db_user = f"customer_app_{uuid4().hex[:12]}"
        db_password = f"pw{uuid4().hex[:20]}"
        database_url = _build_mysql_url(
            host=mysql_admin_runtime.host,
            port=mysql_admin_runtime.port,
            database_name=database_name,
            db_user=db_user,
            db_password=db_password,
        )

        _provision_customer_database(
            mysql_admin_engine,
            database_name=database_name,
            db_user=db_user,
            db_password=db_password,
        )
        _run_alembic_upgrade(database_url)

        runtime = MySqlCustomerRuntime(
            database_url=database_url,
            database_name=database_name,
            db_user=db_user,
            db_password=db_password,
        )
        runtimes.append(runtime)
        return runtime

    try:
        yield factory
    finally:
        for runtime in reversed(runtimes):
            _drop_customer_database(mysql_admin_engine, runtime)


@pytest.fixture
def mysql_customer_runtime(mysql_customer_runtime_factory) -> MySqlCustomerRuntime:
    return mysql_customer_runtime_factory()
