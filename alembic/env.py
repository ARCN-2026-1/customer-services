from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from internal.infrastructure.config.settings import (
    escape_for_alembic_config,
    resolve_alembic_database_url,
)
from internal.infrastructure.persistence.models import Base

config = context.config

if config.config_file_name is not None and not config.attributes.get(
    "skip_logging_config"
):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
ALEMBIC_VERSION_TABLE = "customer_alembic_version"

resolved_database_url = resolve_alembic_database_url(
    config.get_main_option("sqlalchemy.url")
)
config.set_main_option(
    "sqlalchemy.url",
    escape_for_alembic_config(resolved_database_url),
)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        version_table=ALEMBIC_VERSION_TABLE,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=ALEMBIC_VERSION_TABLE,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
