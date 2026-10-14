"""Сервис application, обслуживающий запросы на чтение сохранённых цен.

Это use case только для чтения, который вызывается HTTP-интерфейсом. Он зависит
исключительно от контракта репозитория :class:`PriceRepository` и возвращает
объекты :class:`PriceTickDTO` слою представления.
"""

from __future__ import annotations

from derbit_client.application.dto import PriceTickDTO
from derbit_client.domain.entities import PriceTick
from derbit_client.domain.repositories import PriceRepository


class PriceQueryService:
    """Читает сохранённые индексные цены по запросу API-клиентов."""

    def __init__(self, repository: PriceRepository) -> None:
        self._repository = repository

    async def get_all_prices(self, ticker: str) -> list[PriceTickDTO]:
        """Вернуть все сохранённые цены для ``ticker``."""
        ticks = await self._repository.get_all(ticker)
        return [self._to_dto(tick) for tick in ticks]

    async def get_latest_price(self, ticker: str) -> PriceTickDTO | None:
        """Вернуть самую свежую сохранённую цену для ``ticker``."""
        tick = await self._repository.get_latest(ticker)
        return self._to_dto(tick) if tick is not None else None

    async def get_prices_between(
        self,
        ticker: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[PriceTickDTO]:
        """Вернуть сохранённые цены для ``ticker`` в заданном диапазоне (включительно)."""
        if start is not None and end is not None and start > end:
            raise ValueError("'from' must be less than or equal to 'to'")
        ticks = await self._repository.get_between(ticker, start, end)
        return [self._to_dto(tick) for tick in ticks]

    @staticmethod
    def _to_dto(tick: PriceTick) -> PriceTickDTO:
        return PriceTickDTO(ticker=tick.ticker, price=tick.price, timestamp=tick.timestamp)
