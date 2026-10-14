"""FastAPI application factory.

The factory wires concrete infrastructure adapters (DB engine, HTTP session)
into the application. Collaborators are stored on ``app.state`` and released by
the lifespan context, keeping the module free of mutable globals.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI

from derbit_client.infrastructure.config import Settings, get_settings
from derbit_client.infrastructure.db.session import create_engine, create_session_factory
from derbit_client.interfaces.api.routers import prices


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and dispose infrastructure resources for the app lifetime."""
    settings: Settings = app.state.settings
    engine = create_engine(settings.postgres.dsn())
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.http_session = aiohttp.ClientSession()
    try:
        yield
    finally:
        await app.state.http_session.close()
        await app.state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a configured FastAPI application."""
    app = FastAPI(
        title="Deribit Index Price API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings or get_settings()
    app.include_router(prices.router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
