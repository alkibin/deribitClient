"""FastAPI dependency providers.

All dependencies read their collaborators from ``app.state`` (populated by the
application lifespan) so that no module-level mutable state is required. The API
only needs read access, so it depends on the query service and never on the
Deribit client.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from derbit_client.application.price_query import PriceQueryService
from derbit_client.infrastructure.config import Settings
from derbit_client.infrastructure.db.repository import SqlAlchemyPriceRepository


def get_settings(request: Request) -> Settings:
    """Return the settings instance stored on the application state."""
    return request.app.state.settings


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """Return the session factory stored on the application state."""
    return request.app.state.session_factory


async def get_repository(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncIterator[SqlAlchemyPriceRepository]:
    """Yield a repository bound to a per-request session."""
    async with session_factory() as session:
        yield SqlAlchemyPriceRepository(session)


def get_query_service(
    repository: SqlAlchemyPriceRepository = Depends(get_repository),
) -> PriceQueryService:
    """Assemble the read-only :class:`PriceQueryService` for the current request."""
    return PriceQueryService(reader=repository)
