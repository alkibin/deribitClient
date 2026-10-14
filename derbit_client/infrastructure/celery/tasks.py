"""Периодические задачи Celery.

Единственный модульный объект ``celery_app`` — это точка входа, необходимая
Celery CLI (``celery -A derbit_client.infrastructure.celery.tasks``). Он не
хранит состояние приложения: все зависимости создаются внутри задачи из
:class:`Settings`.
"""

from __future__ import annotations

import asyncio

import aiohttp

from derbit_client.application.price_ingestion import PriceIngestionService
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
    """Загрузить текущие индексные цены и сохранить их в одной транзакции."""
    engine = create_engine(settings.postgres.dsn())
    session_factory = create_session_factory(engine)
    try:
        async with aiohttp.ClientSession() as http_session:
            provider = DeribitClient(
                session=http_session,
                base_url=settings.deribit.base_url,
                timeout=settings.deribit.timeout,
                max_retries=settings.deribit.max_retries,
                backoff_base=settings.deribit.backoff_base,
                backoff_max=settings.deribit.backoff_max,
            )
            async with session_scope(session_factory) as db_session:
                service = PriceIngestionService(
                    repository=SqlAlchemyPriceRepository(db_session),
                    provider=provider,
                )
                await service.fetch_and_store(tickers)
        return tickers
    finally:
        await engine.dispose()


@celery_app.task(name=TASK_FETCH_PRICES)
def fetch_index_prices() -> list[str]:
    """Задача Celery: загрузить и сохранить индексные цены по всем настроенным тикерам."""
    settings = get_settings()
    return asyncio.run(_fetch_and_store_prices(settings, settings.deribit.tickers))
