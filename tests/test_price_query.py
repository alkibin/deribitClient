"""Тесты сервиса чтения цен на основе in-memory фейков."""

from decimal import Decimal

from src.application.price_query import PriceQueryService
from src.domain.entities import PriceTick
from src.application.ports import PriceRepository


class FakeRepository(PriceRepository):
    """In-memory репозиторий для изоляции сервиса от базы данных."""

    def __init__(self, ticks: list[PriceTick] | None = None) -> None:
        self.ticks = list(ticks or [])

    async def add_many(self, ticks: list[PriceTick]) -> None:
        self.ticks.extend(ticks)

    async def get_all(
        self, ticker: str, *, limit: int | None = None, offset: int = 0
    ) -> list[PriceTick]:
        ordered = sorted(
            (tick for tick in self.ticks if tick.ticker == ticker),
            key=lambda tick: tick.timestamp,
        )
        return ordered[offset:] if limit is None else ordered[offset : offset + limit]

    async def count(self, ticker: str) -> int:
        return sum(1 for tick in self.ticks if tick.ticker == ticker)

    async def get_latest(self, ticker: str) -> PriceTick | None:
        matching = [tick for tick in self.ticks if tick.ticker == ticker]
        return max(matching, key=lambda tick: tick.timestamp) if matching else None

    async def get_between(
        self,
        ticker: str,
        *,
        start: int | None = None,
        end: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[PriceTick]:
        matched = [
            tick
            for tick in await self.get_all(ticker)
            if (start is None or tick.timestamp >= start) and (end is None or tick.timestamp <= end)
        ]
        return matched[offset:] if limit is None else matched[offset : offset + limit]

    async def count_between(
        self, ticker: str, *, start: int | None = None, end: int | None = None
    ) -> int:
        return len(await self.get_between(ticker, start=start, end=end))


async def test_get_all_prices_returns_stored_ticks() -> None:
    repository = FakeRepository(
        [
            PriceTick(ticker="btc_usd", price=Decimal("1"), timestamp=1),
            PriceTick(ticker="btc_usd", price=Decimal("2"), timestamp=2),
            PriceTick(ticker="eth_usd", price=Decimal("3"), timestamp=3),
        ]
    )
    service = PriceQueryService(repository=repository)

    page = await service.get_all_prices("btc_usd")

    assert [tick.timestamp for tick in page.items] == [1, 2]
    assert page.total == 2


async def test_get_all_prices_paginates() -> None:
    repository = FakeRepository(
        [PriceTick(ticker="btc_usd", price=Decimal(i), timestamp=i) for i in range(1, 6)]
    )
    service = PriceQueryService(repository=repository)

    page = await service.get_all_prices("btc_usd", limit=2, offset=1)

    assert [tick.timestamp for tick in page.items] == [2, 3]
    assert (page.total, page.limit, page.offset) == (5, 2, 1)


async def test_get_latest_price_returns_none_when_empty() -> None:
    service = PriceQueryService(repository=FakeRepository())
    assert await service.get_latest_price("btc_usd") is None


async def test_get_prices_between_does_not_validate_range() -> None:
    service = PriceQueryService(repository=FakeRepository())
    page = await service.get_prices_between("btc_usd", start=10, end=5)
    assert page.items == []
    assert page.total == 0


async def test_get_prices_between_filters() -> None:
    repository = FakeRepository(
        [PriceTick(ticker="btc_usd", price=Decimal(i), timestamp=i) for i in range(1, 6)]
    )
    service = PriceQueryService(repository=repository)

    page = await service.get_prices_between("btc_usd", start=2, end=4)

    assert [tick.timestamp for tick in page.items] == [2, 3, 4]
    assert page.total == 3
