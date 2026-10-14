"""Периодические задачи Celery."""

import asyncio

from src.infrastructure.celery.app import TASK_FETCH_PRICES, build_celery_app
from src.core.config import get_settings
from src.infrastructure.celery.services import fetch_and_store_prices

celery_app = build_celery_app(get_settings())


@celery_app.task(name=TASK_FETCH_PRICES)
def fetch_index_prices() -> list[str]:
    """Задача Celery: загрузить и сохранить индексные цены по всем настроенным тикерам."""
    settings = get_settings()
    return asyncio.run(
        fetch_and_store_prices(settings, settings.deribit.tickers)
    )
