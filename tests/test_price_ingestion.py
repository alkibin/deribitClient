"""Тесты сервиса загрузки цен на моках."""

from decimal import Decimal
from unittest.mock import AsyncMock, create_autospec

import pytest

from src.application.ports import PriceRepository
from src.application.price_ingestion import PriceIngestionService


@pytest.fixture
def repository() -> PriceRepository:
    """Репозиторий-двойник: реальная БД не нужна."""
    return create_autospec(PriceRepository, instance=True)


@pytest.fixture
def service(repository: PriceRepository) -> PriceIngestionService:
    """Сервис с провайдером, отвечающим по словарю цен."""
    return PriceIngestionService(repository=repository, provider=AsyncMock())


def _provider_prices(**values: str) -> dict[str, Decimal]:
    return {ticker: Decimal(value) for ticker, value in values.items()}


async def test_fetch_and_store_persists_all_tickers(repository, service) -> None:
    service.provider.get_index_price.side_effect = _provider_prices(
        btc_usd="100", eth_usd="20"
    ).__getitem__

    await service.fetch_and_store(["btc_usd", "eth_usd"])

    repository.add_many.assert_awaited_once()
    stored = repository.add_many.await_args.args[0]
    assert {tick.ticker for tick in stored} == {"btc_usd", "eth_usd"}
    assert {tick.price for tick in stored} == {Decimal("100"), Decimal("20")}


async def test_fetch_and_store_uses_single_timestamp_for_batch(repository, service) -> None:
    service.provider.get_index_price.side_effect = _provider_prices(
        btc_usd="1", eth_usd="2"
    ).__getitem__

    await service.fetch_and_store(["btc_usd", "eth_usd"])

    stored = repository.add_many.await_args.args[0]
    assert len({tick.timestamp for tick in stored}) == 1


async def test_fetch_and_store_with_no_tickers_does_not_read_prices(repository, service) -> None:
    await service.fetch_and_store([])

    repository.add_many.assert_awaited_once_with([])
    service.provider.get_index_price.assert_not_awaited()
