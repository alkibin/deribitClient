#!/usr/bin/env sh
set -eu

if [ "${WAIT_FOR_DB:-true}" = "true" ]; then
    python -m src.infrastructure.db.wait_for_db
fi

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Applying database migrations..."
    alembic upgrade head
fi

exec "$@"
