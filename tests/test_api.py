"""Тесты HTTP-слоя на ASGI-transport с заглушкой сервиса."""

from collections.abc import AsyncIterator
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.dto import Page, PriceTickDTO
from src.interfaces.api.app_factory import create_app
from src.interfaces.api.di import get_query_service


@pytest.fixture
def service() -> AsyncMock:
    """Заглушка :class:`PriceQueryService` с настраиваемыми ответами."""
    return AsyncMock()


@pytest.fixture
async def client(service: AsyncMock) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_query_service] = lambda: service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


def page(
    *timestamps: int,
    total: int | None = None,
    limit: int = 50,
    offset: int = 0
):
    items = [
        PriceTickDTO(ticker="btc_usd", price=Decimal(timestamp), timestamp=timestamp)
        for timestamp in timestamps
    ]
    return Page(
        items=items,
        total=len(timestamps) if total is None else total,
        limit=limit,
        offset=offset,
    )


async def test_get_all_prices_returns_page(client: AsyncClient, service: AsyncMock) -> None:
    service.get_all_prices.return_value = page(1000, 2000)

    response = await client.get("/api/v1/prices", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    body = response.json()
    assert [tick["timestamp"] for tick in body["items"]] == [1000, 2000]
    assert (body["total"], body["limit"], body["offset"]) == (2, 50, 0)
    service.get_all_prices.assert_awaited_once_with("btc_usd", limit=50, offset=0)


async def test_get_all_prices_forwards_pagination(client: AsyncClient, service: AsyncMock) -> None:
    service.get_all_prices.return_value = page(2000, total=2, limit=1, offset=1)

    response = await client.get(
        "/api/v1/prices",
        params={"ticker": "btc_usd", "limit": 1, "offset": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert [tick["timestamp"] for tick in body["items"]] == [2000]
    assert (body["total"], body["limit"], body["offset"]) == (2, 1, 1)


async def test_get_all_prices_rejects_limit_above_max(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/prices",
        params={"ticker": "btc_usd", "limit": 100000},
    )
    assert response.status_code == 422


async def test_get_all_prices_requires_ticker(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices")
    assert response.status_code == 422


async def test_get_latest_price(client: AsyncClient, service: AsyncMock) -> None:
    service.get_latest_price.return_value = PriceTickDTO(
        ticker="btc_usd", price=Decimal("100"), timestamp=2000
    )

    response = await client.get("/api/v1/prices/latest", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    assert response.json()["timestamp"] == 2000


async def test_get_latest_price_not_found(client: AsyncClient, service: AsyncMock) -> None:
    service.get_latest_price.return_value = None

    response = await client.get("/api/v1/prices/latest", params={"ticker": "unknown"})

    assert response.status_code == 404
    assert response.json() == {"detail": "No data for ticker 'unknown'"}


async def test_get_prices_by_date_filter(client: AsyncClient, service: AsyncMock) -> None:
    service.get_prices_between.return_value = page(2000, total=1)

    response = await client.get(
        "/api/v1/prices/filter",
        params={"ticker": "btc_usd", "from": 1500, "to": 2500},
    )

    assert response.status_code == 200
    body = response.json()
    assert [tick["timestamp"] for tick in body["items"]] == [2000]
    assert body["total"] == 1
    service.get_prices_between.assert_awaited_once_with(
        "btc_usd", start=1500, end=2500, limit=50, offset=0
    )


async def test_get_prices_by_date_rejects_inverted_range(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/prices/filter",
        params={"ticker": "btc_usd", "from": 2500, "to": 1500},
    )
    assert response.status_code == 422


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
