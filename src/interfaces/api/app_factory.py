"""Фабрика приложения FastAPI.

Фабрика связывает конкретные инфраструктурные адаптеры (движок базы) с
приложением. Соавторы сохраняются в ``app.state`` и освобождаются в lifespan, что
избавляет модуль от изменяемых глобальных переменных. HTTP-приложение работает
только на чтение и не нуждается в клиенте стороннего API.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import Settings, get_settings
from src.infrastructure.db.session import create_engine, create_session_factory
from src.interfaces.api.routers import prices


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Создать и освободить инфраструктурные ресурсы на время жизни приложения."""
    settings: Settings = app.state.settings
    engine = create_engine(settings.postgres.dsn())
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        await app.state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Собрать настроенное приложение FastAPI."""
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
