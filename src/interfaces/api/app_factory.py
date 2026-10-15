"""Фабрика приложения FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import Settings, get_settings
from src.infrastructure.db.session import create_engine, create_session_factory
from src.interfaces.api.exceptions import register_exception_handlers
from src.interfaces.api.routers import prices


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Создать и освободить инфраструктурные ресурсы на время жизни приложения."""
    settings = get_settings()
    engine = create_engine(settings.postgres.dsn)
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    """Собрать настроенное приложение FastAPI."""
    settings = get_settings()
    app = FastAPI(
        title=settings.api.title,
        version=settings.api.version,
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(prices.router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
