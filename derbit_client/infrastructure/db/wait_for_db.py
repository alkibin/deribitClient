"""Ожидание готовности PostgreSQL принимать соединения.

Используется как вспомогательный скрипт в entrypoint контейнера, чтобы миграции
и воркеры не соревновались с базой во время запуска.
"""

from __future__ import annotations

import asyncio
import sys

import asyncpg

from derbit_client.infrastructure.config import get_settings

MAX_ATTEMPTS = 30
DELAY_SECONDS = 2


async def wait_for_database() -> None:
    """Опрашивать PostgreSQL до установления соединения или исчерпания попыток."""
    dsn = get_settings().postgres.dsn(driver="postgresql")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            connection = await asyncpg.connect(dsn)
            await connection.close()
            print(f"Database is ready (attempt {attempt}).")
            return
        except (OSError, asyncpg.PostgresError) as error:
            print(f"Database not ready (attempt {attempt}/{MAX_ATTEMPTS}): {error}")
            await asyncio.sleep(DELAY_SECONDS)
    print("Database did not become available in time.", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(wait_for_database())
