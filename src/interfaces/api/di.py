"""Провайдеры зависимостей FastAPI."""

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.application.price_query import PriceQueryService
from src.infrastructure.db.repository import SqlAlchemyPriceRepository


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """Вернуть фабрику сессий, сохранённую в состоянии приложения."""
    return request.app.state.session_factory


async def get_repository(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncIterator[SqlAlchemyPriceRepository]:
    """Отдать репозиторий, привязанный к сессии текущего запроса."""
    async with session_factory() as session:
        yield SqlAlchemyPriceRepository(session)


def get_query_service(
    repository: SqlAlchemyPriceRepository = Depends(get_repository),
) -> PriceQueryService:
    """Собрать доступный только для чтения :class:`PriceQueryService` для запроса."""
    return PriceQueryService(repository=repository)
