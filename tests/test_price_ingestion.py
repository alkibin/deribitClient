"""Тесты сервиса загрузки цен на основе in-memory фейков."""

from __future__ import annotations

from decimal import Decimal

from derbit_client.application.price_ingestion import PriceIngestionService
from derbit_client.domain.entities import PriceTick
from derbit_client.domain.repositories import PriceRepository


class FakeRepository(PriceRepository):
    """In-memory репозиторий для изоляции сервиса от базы данных."""

    def __init__(self) -> None:
        self.add_calls: list[list[PriceTick]] = []

    async def add_many(self, ticks: list[PriceTick]) -> None:
        self.add_calls.append(ticks)

    async def get_all(self, ticker: str) -> list[PriceTick]:
        return []

    async def get_latest(self, ticker: str) -> PriceTick | None:
        return None

    async def get_between(
        self, ticker: str, start: int | None = None, end: int | None = None
    ) -> list[PriceTick]:
        return []


class FakeProvider:
    """Детерминированный провайдер индексных цен."""

    def __init__(self, prices: dict[str, Decimal]) -> None:
        self._prices = prices
        self.requested: list[str] = []

    async def get_index_price(self, ticker: str) -> Decimal:
        self.requested.append(ticker)
        return self._prices[ticker]


async def test_fetch_and_store_persists_all_tickers() -> None:
    repository = FakeRepository()
    provider = FakeProvider({"btc_usd": Decimal("100"), "eth_usd": Decimal("20")})
    service = PriceIngestionService(repository=repository, provider=provider)

    result = await service.fetch_and_store(["btc_usd", "eth_usd"])

    assert result is None
    assert provider.requested == ["btc_usd", "eth_usd"]
    assert len(repository.add_calls) == 1
    stored = repository.add_calls[0]
    assert {tick.ticker for tick in stored} == {"btc_usd", "eth_usd"}


async def test_fetch_and_store_uses_single_timestamp_for_batch() -> None:
    repository = FakeRepository()
    provider = FakeProvider({"btc_usd": Decimal("1"), "eth_usd": Decimal("2")})
    service = PriceIngestionService(repository=repository, provider=provider)

    await service.fetch_and_store(["btc_usd", "eth_usd"])

    timestamps = {tick.timestamp for tick in repository.add_calls[0]}
    assert len(timestamps) == 1


async def test_fetch_and_store_with_no_tickers_does_not_write() -> None:
    repository = FakeRepository()
    service = PriceIngestionService(repository=repository, provider=FakeProvider({}))

    await service.fetch_and_store([])

    assert repository.add_calls == [[]]
