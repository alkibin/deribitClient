"""Сервис application, отвечающий за загрузку индексных цен."""

from datetime import UTC, datetime

from src.application.ports import IndexPriceProvider
from src.domain.entities import PriceTick
from src.domain.repositories import PriceRepository


class PriceIngestionService:
    """Загружает текущие индексные цены и сохраняет их."""

    def __init__(self, repository: PriceRepository, provider: IndexPriceProvider) -> None:
        self.repo = repository
        self.provider = provider

    async def fetch_and_store(self, tickers: list[str]) -> None:
        """Загрузить текущую индексную цену для каждого тикера и сохранить."""
        observed_at = int(datetime.now(tz=UTC).timestamp())
        ticks: list[PriceTick] = []
        for ticker in tickers:
            price = await self.provider.get_index_price(ticker)
            ticks.append(PriceTick(ticker=ticker, price=price, timestamp=observed_at))
        await self.repo.add_many(ticks)
