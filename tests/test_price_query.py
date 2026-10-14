"""Тесты сервиса чтения цен на моках репозитория."""

from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from src.application.ports import PriceRepository
from src.application.price_query import PriceQueryService
from src.domain.entities import PriceTick


@pytest.fixture
def repository() -> PriceRepository:
    """Репозиторий-двойник: реальная БД не нужна."""
    return create_autospec(PriceRepository, instance=True)


@pytest.fixture
def service(repository: PriceRepository) -> PriceQueryService:
    return PriceQueryService(repository=repository)


def _tick(timestamp: int) -> PriceTick:
    return PriceTick(ticker="btc_usd", price=Decimal(timestamp), timestamp=timestamp)


async def test_get_all_prices_returns_page(repository, service) -> None:
    repository.count.return_value = 2
    repository.get_all.return_value = [_tick(1), _tick(2)]

    page = await service.get_all_prices("btc_usd")

    assert [tick.timestamp for tick in page.items] == [1, 2]
    assert page.total == 2
    repository.get_all.assert_awaited_once_with("btc_usd", limit=None, offset=0)


async def test_get_all_prices_forwards_pagination(repository, service) -> None:
    repository.count.return_value = 5
    repository.get_all.return_value = [_tick(2), _tick(3)]

    page = await service.get_all_prices("btc_usd", limit=2, offset=1)

    assert [tick.timestamp for tick in page.items] == [2, 3]
    assert (page.total, page.limit, page.offset) == (5, 2, 1)
    repository.get_all.assert_awaited_once_with("btc_usd", limit=2, offset=1)


async def test_get_latest_price_returns_none_when_empty(repository, service) -> None:
    repository.get_latest.return_value = None

    assert await service.get_latest_price("btc_usd") is None


async def test_get_prices_between_returns_page(repository, service) -> None:
    repository.count_between.return_value = 3
    repository.get_between.return_value = [_tick(2), _tick(3), _tick(4)]

    page = await service.get_prices_between("btc_usd", start=2, end=4)

    assert [tick.timestamp for tick in page.items] == [2, 3, 4]
    assert page.total == 3
    repository.get_between.assert_awaited_once_with("btc_usd", start=2, end=4, limit=None, offset=0)


async def test_get_prices_between_does_not_validate_range(repository, service) -> None:
    repository.count_between.return_value = 0
    repository.get_between.return_value = []

    page = await service.get_prices_between("btc_usd", start=10, end=5)

    assert page.items == []
    assert page.total == 0
