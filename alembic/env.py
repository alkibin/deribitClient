"""Окружение Alembic (асинхронное).

URL базы берётся из настроек приложения, поэтому миграции всегда нацелены на ту
же БД, что и рантайм, а учётные данные не дублируются в конфигурации.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

from alembic import context
from derbit_client.core.config import get_settings

# Import models so their tables are registered on Base.metadata.
from derbit_client.infrastructure.db import models  # noqa: F401
from derbit_client.infrastructure.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().postgres.dsn())

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запустить миграции в offline-режиме (вывод SQL без подключения к БД)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Запустить миграции в online-режиме с использованием асинхронного движка."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
