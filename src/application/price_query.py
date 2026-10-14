"""Сервис application, обслуживающий запросы на чтение сохранённых цен."""

from src.application.dto import PriceTickDTO
from src.domain.entities import PriceTick
from src.domain.repositories import PriceRepository


class PriceQueryService:
    """Читает сохранённые индексные цены по запросу API-клиентов."""

    def __init__(self, repository: PriceRepository) -> None:
        self.repo = repository

    async def get_all_prices(self, ticker: str) -> list[PriceTickDTO]:
        """Вернуть все сохранённые цены для ``ticker``."""
        ticks = await self.repo.get_all(ticker)
        return [self._to_dto(tick) for tick in ticks]

    async def get_latest_price(self, ticker: str) -> PriceTickDTO | None:
        """Вернуть самую свежую сохранённую цену для ``ticker``."""
        tick = await self.repo.get_latest(ticker)
        return self._to_dto(tick) if tick is not None else None

    async def get_prices_between(
        self,
        ticker: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[PriceTickDTO]:
        """Вернуть сохранённые цены для ``ticker`` в заданном диапазоне (включительно)."""
        ticks = await self.repo.get_between(ticker, start, end)
        return [self._to_dto(tick) for tick in ticks]

    @staticmethod
    def _to_dto(tick: PriceTick) -> PriceTickDTO:
        return PriceTickDTO(ticker=tick.ticker, price=tick.price, timestamp=tick.timestamp)
