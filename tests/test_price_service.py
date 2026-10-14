"""Tests for the application service using in-memory fakes."""

from __future__ import annotations

from decimal import Decimal

import pytest

from derbit_client.application.services import PriceService
from derbit_client.domain.entities import PriceTick
from derbit_client.domain.repositories import PriceRepository


class FakeRepository(PriceRepository):
    """In-memory repository used to isolate the service from the database."""

    def __init__(self, ticks: list[PriceTick] | None = None) -> None:
        self.ticks: list[PriceTick] = list(ticks or [])
        self.add_calls: list[list[PriceTick]] = []

    async def add_many(self, ticks: list[PriceTick]) -> None:
        self.add_calls.append(ticks)
        self.ticks.extend(ticks)

    async def get_all(self, ticker: str) -> list[PriceTick]:
        return sorted(
            (tick for tick in self.ticks if tick.ticker == ticker),
            key=lambda tick: tick.timestamp,
        )

    async def get_latest(self, ticker: str) -> PriceTick | None:
        matching = [tick for tick in self.ticks if tick.ticker == ticker]
        return max(matching, key=lambda tick: tick.timestamp) if matching else None

    async def get_between(
        self, ticker: str, start: int | None = None, end: int | None = None
    ) -> list[PriceTick]:
        return [
            tick
            for tick in await self.get_all(ticker)
            if (start is None or tick.timestamp >= start) and (end is None or tick.timestamp <= end)
        ]


class FakeProvider:
    """Deterministic index price provider."""

    def __init__(self, prices: dict[str, Decimal]) -> None:
        self._prices = prices
        self.requested: list[str] = []

    async def get_index_price(self, ticker: str) -> Decimal:
        self.requested.append(ticker)
        return self._prices[ticker]


async def test_fetch_and_store_persists_all_tickers() -> None:
    repository = FakeRepository()
    provider = FakeProvider({"btc_usd": Decimal("100"), "eth_usd": Decimal("20")})
    service = PriceService(repository=repository, provider=provider)

    stored = await service.fetch_and_store(["btc_usd", "eth_usd"])

    assert provider.requested == ["btc_usd", "eth_usd"]
    assert {tick.ticker for tick in stored} == {"btc_usd", "eth_usd"}
    assert len(repository.add_calls) == 1
    # A single observation timestamp is shared by the whole batch.
    assert len({tick.timestamp for tick in stored}) == 1


async def test_get_all_prices_returns_stored_ticks() -> None:
    repository = FakeRepository(
        [
            PriceTick(ticker="btc_usd", price=Decimal("1"), timestamp=1),
            PriceTick(ticker="btc_usd", price=Decimal("2"), timestamp=2),
            PriceTick(ticker="eth_usd", price=Decimal("3"), timestamp=3),
        ]
    )
    service = PriceService(repository=repository, provider=FakeProvider({}))

    result = await service.get_all_prices("btc_usd")

    assert [tick.timestamp for tick in result] == [1, 2]


async def test_get_latest_price_returns_none_when_empty() -> None:
    service = PriceService(repository=FakeRepository(), provider=FakeProvider({}))
    assert await service.get_latest_price("btc_usd") is None


async def test_get_prices_between_validates_range() -> None:
    service = PriceService(repository=FakeRepository(), provider=FakeProvider({}))
    with pytest.raises(ValueError):
        await service.get_prices_between("btc_usd", start=10, end=5)


async def test_get_prices_between_filters() -> None:
    repository = FakeRepository(
        [PriceTick(ticker="btc_usd", price=Decimal(i), timestamp=i) for i in range(1, 6)]
    )
    service = PriceService(repository=repository, provider=FakeProvider({}))

    result = await service.get_prices_between("btc_usd", start=2, end=4)

    assert [tick.timestamp for tick in result] == [2, 3, 4]
