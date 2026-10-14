"""Сервис application, обслуживающий запросы на чтение сохранённых цен."""

from src.application.dto import Page, PriceTickDTO
from src.domain.entities import PriceTick
from src.domain.repositories import PriceRepository


class PriceQueryService:
    """Читает сохранённые индексные цены по запросу API-клиентов."""

    def __init__(self, repository: PriceRepository) -> None:
        self.repo = repository

    async def get_all_prices(
        self,
        ticker: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[PriceTickDTO]:
        """Вернуть страницу сохранённых цен для ``ticker`` и их общее число."""
        total = await self.repo.count(ticker)
        ticks = await self.repo.get_all(ticker, limit=limit, offset=offset)
        return self._to_page(ticks, total=total, limit=limit, offset=offset)

    async def get_latest_price(self, ticker: str) -> PriceTickDTO | None:
        """Вернуть самую свежую сохранённую цену для ``ticker``."""
        tick = await self.repo.get_latest(ticker)
        return self._to_dto(tick) if tick is not None else None

    async def get_prices_between(
        self,
        ticker: str,
        *,
        start: int | None = None,
        end: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[PriceTickDTO]:
        """Вернуть страницу цен ticker в диапазоне (включительно) и их число."""
        total = await self.repo.count_between(ticker, start=start, end=end)
        ticks = await self.repo.get_between(
            ticker, start=start, end=end, limit=limit, offset=offset
        )
        return self._to_page(ticks, total=total, limit=limit, offset=offset)

    @staticmethod
    def _to_page(
        ticks: list[PriceTick],
        *,
        total: int,
        limit: int | None,
        offset: int,
    ) -> Page[PriceTickDTO]:
        return Page(
            items=[PriceQueryService._to_dto(tick) for tick in ticks],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def _to_dto(tick: PriceTick) -> PriceTickDTO:
        return PriceTickDTO(ticker=tick.ticker, price=tick.price, timestamp=tick.timestamp)
