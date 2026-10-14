"""Tests for the price ingestion service using in-memory fakes."""

from __future__ import annotations

from decimal import Decimal

from derbit_client.application.price_ingestion import PriceIngestionService
from derbit_client.domain.entities import PriceTick
from derbit_client.domain.repositories import PriceWriter


class FakeWriter(PriceWriter):
    """In-memory write-side repository."""

    def __init__(self) -> None:
        self.add_calls: list[list[PriceTick]] = []

    async def add_many(self, ticks: list[PriceTick]) -> None:
        self.add_calls.append(ticks)


class FakeProvider:
    """Deterministic index price provider."""

    def __init__(self, prices: dict[str, Decimal]) -> None:
        self._prices = prices
        self.requested: list[str] = []

    async def get_index_price(self, ticker: str) -> Decimal:
        self.requested.append(ticker)
        return self._prices[ticker]


async def test_fetch_and_store_persists_all_tickers() -> None:
    writer = FakeWriter()
    provider = FakeProvider({"btc_usd": Decimal("100"), "eth_usd": Decimal("20")})
    service = PriceIngestionService(writer=writer, provider=provider)

    result = await service.fetch_and_store(["btc_usd", "eth_usd"])

    assert result is None
    assert provider.requested == ["btc_usd", "eth_usd"]
    assert len(writer.add_calls) == 1
    stored = writer.add_calls[0]
    assert {tick.ticker for tick in stored} == {"btc_usd", "eth_usd"}


async def test_fetch_and_store_uses_single_timestamp_for_batch() -> None:
    writer = FakeWriter()
    provider = FakeProvider({"btc_usd": Decimal("1"), "eth_usd": Decimal("2")})
    service = PriceIngestionService(writer=writer, provider=provider)

    await service.fetch_and_store(["btc_usd", "eth_usd"])

    timestamps = {tick.timestamp for tick in writer.add_calls[0]}
    assert len(timestamps) == 1


async def test_fetch_and_store_with_no_tickers_does_not_write() -> None:
    writer = FakeWriter()
    service = PriceIngestionService(writer=writer, provider=FakeProvider({}))

    await service.fetch_and_store([])

    assert writer.add_calls == [[]]
