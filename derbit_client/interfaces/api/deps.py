"""FastAPI dependency providers.

All dependencies read their collaborators from ``app.state`` (populated by the
application lifespan) so that no module-level mutable state is required.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import aiohttp
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from derbit_client.application.services import PriceService
from derbit_client.infrastructure.config import Settings
from derbit_client.infrastructure.db.repository import SqlAlchemyPriceRepository
from derbit_client.infrastructure.deribit.client import DeribitClient, IndexPriceProvider


def get_settings(request: Request) -> Settings:
    """Return the settings instance stored on the application state."""
    return request.app.state.settings


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """Return the session factory stored on the application state."""
    return request.app.state.session_factory


def get_http_session(request: Request) -> aiohttp.ClientSession:
    """Return the shared aiohttp session stored on the application state."""
    return request.app.state.http_session


async def get_repository(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncIterator[SqlAlchemyPriceRepository]:
    """Yield a repository bound to a per-request session."""
    async with session_factory() as session:
        yield SqlAlchemyPriceRepository(session)


def get_price_provider(
    http_session: aiohttp.ClientSession = Depends(get_http_session),
    settings: Settings = Depends(get_settings),
) -> IndexPriceProvider:
    """Build a Deribit index price provider for the current request."""
    return DeribitClient(
        session=http_session,
        base_url=settings.deribit.base_url,
        timeout=settings.deribit.timeout,
    )


def get_price_service(
    repository: SqlAlchemyPriceRepository = Depends(get_repository),
    provider: IndexPriceProvider = Depends(get_price_provider),
) -> PriceService:
    """Assemble the :class:`PriceService` use case for the current request."""
    return PriceService(repository=repository, provider=provider)
