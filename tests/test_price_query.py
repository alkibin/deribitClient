"""Tests for the read-only price query service using an in-memory fake."""

from __future__ import annotations

from decimal import Decimal

import pytest

from derbit_client.application.price_query import PriceQueryService
from derbit_client.domain.entities import PriceTick
from derbit_client.domain.repositories import PriceReader


class FakeReader(PriceReader):
    """In-memory read-side repository."""

    def __init__(self, ticks: list[PriceTick] | None = None) -> None:
        self.ticks: list[PriceTick] = list(ticks or [])

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


async def test_get_all_prices_returns_stored_ticks() -> None:
    reader = FakeReader(
        [
            PriceTick(ticker="btc_usd", price=Decimal("1"), timestamp=1),
            PriceTick(ticker="btc_usd", price=Decimal("2"), timestamp=2),
            PriceTick(ticker="eth_usd", price=Decimal("3"), timestamp=3),
        ]
    )
    service = PriceQueryService(reader=reader)

    result = await service.get_all_prices("btc_usd")

    assert [tick.timestamp for tick in result] == [1, 2]


async def test_get_latest_price_returns_none_when_empty() -> None:
    service = PriceQueryService(reader=FakeReader())
    assert await service.get_latest_price("btc_usd") is None


async def test_get_prices_between_validates_range() -> None:
    service = PriceQueryService(reader=FakeReader())
    with pytest.raises(ValueError):
        await service.get_prices_between("btc_usd", start=10, end=5)


async def test_get_prices_between_filters() -> None:
    reader = FakeReader(
        [PriceTick(ticker="btc_usd", price=Decimal(i), timestamp=i) for i in range(1, 6)]
    )
    service = PriceQueryService(reader=reader)

    result = await service.get_prices_between("btc_usd", start=2, end=4)

    assert [tick.timestamp for tick in result] == [2, 3, 4]
