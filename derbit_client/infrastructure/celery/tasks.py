"""Periodic Celery tasks.

The single module-level ``celery_app`` object is a framework entrypoint needed
by the Celery CLI (``celery -A derbit_client.infrastructure.celery.tasks``). It
holds no application state: every dependency is constructed inside the task
from :class:`Settings`.
"""

from __future__ import annotations

import asyncio

import aiohttp

from derbit_client.application.services import PriceService
from derbit_client.infrastructure.celery.app import TASK_FETCH_PRICES, build_celery_app
from derbit_client.infrastructure.config import Settings, get_settings
from derbit_client.infrastructure.db.repository import SqlAlchemyPriceRepository
from derbit_client.infrastructure.db.session import (
    create_engine,
    create_session_factory,
    session_scope,
)
from derbit_client.infrastructure.deribit.client import DeribitClient

celery_app = build_celery_app(get_settings())


async def _fetch_and_store_prices(settings: Settings, tickers: list[str]) -> list[str]:
    """Fetch current index prices and persist them within one transaction."""
    engine = create_engine(settings.postgres.dsn())
    session_factory = create_session_factory(engine)
    try:
        async with aiohttp.ClientSession() as http_session:
            provider = DeribitClient(
                session=http_session,
                base_url=settings.deribit.base_url,
                timeout=settings.deribit.timeout,
            )
            async with session_scope(session_factory) as db_session:
                service = PriceService(
                    repository=SqlAlchemyPriceRepository(db_session),
                    provider=provider,
                )
                stored = await service.fetch_and_store(tickers)
        return [tick.ticker for tick in stored]
    finally:
        await engine.dispose()


@celery_app.task(name=TASK_FETCH_PRICES)
def fetch_index_prices() -> list[str]:
    """Celery task: fetch and store index prices for all configured tickers."""
    settings = get_settings()
    return asyncio.run(_fetch_and_store_prices(settings, settings.deribit.tickers))
