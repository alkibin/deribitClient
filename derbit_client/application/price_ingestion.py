"""Сервис application, отвечающий за загрузку индексных цен.

Это use case только для записи, который вызывается плановым воркером Celery. Он
зависит исключительно от исходящего порта :class:`IndexPriceProvider` и контракта
репозитория :class:`PriceRepository` и ничего не знает про HTTP API.
"""

from __future__ import annotations

from datetime import UTC, datetime

from derbit_client.application.ports import IndexPriceProvider
from derbit_client.domain.entities import PriceTick
from derbit_client.domain.repositories import PriceRepository


class PriceIngestionService:
    """Загружает текущие индексные цены и сохраняет их."""

    def __init__(self, repository: PriceRepository, provider: IndexPriceProvider) -> None:
        self._repository = repository
        self._provider = provider

    async def fetch_and_store(self, tickers: list[str]) -> None:
        """Загрузить текущую индексную цену для каждого тикера и сохранить их.

        Для всего батча фиксируется единый UNIX timestamp, чтобы все цены,
        собранные за один запуск, имели общее время наблюдения.
        """
        observed_at = int(datetime.now(tz=UTC).timestamp())
        ticks: list[PriceTick] = []
        for ticker in tickers:
            price = await self._provider.get_index_price(ticker)
            ticks.append(PriceTick(ticker=ticker, price=price, timestamp=observed_at))
        await self._repository.add_many(ticks)
