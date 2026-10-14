"""Tests for the HTTP layer using an ASGI transport and a fake service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from derbit_client.application.dto import PriceTickDTO
from derbit_client.interfaces.api.app_factory import create_app
from derbit_client.interfaces.api.deps import get_query_service


class FakePriceQueryService:
    """Stub service returning canned DTOs for endpoint tests."""

    def __init__(self) -> None:
        self._data = [
            PriceTickDTO(ticker="btc_usd", price=Decimal("100"), timestamp=1000),
            PriceTickDTO(ticker="btc_usd", price=Decimal("200"), timestamp=2000),
        ]

    async def get_all_prices(self, ticker: str) -> list[PriceTickDTO]:
        return [tick for tick in self._data if tick.ticker == ticker]

    async def get_latest_price(self, ticker: str) -> PriceTickDTO | None:
        matching = [tick for tick in self._data if tick.ticker == ticker]
        return matching[-1] if matching else None

    async def get_prices_between(
        self, ticker: str, start: int | None = None, end: int | None = None
    ) -> list[PriceTickDTO]:
        return [
            tick
            for tick in self._data
            if tick.ticker == ticker
            and (start is None or tick.timestamp >= start)
            and (end is None or tick.timestamp <= end)
        ]


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_query_service] = lambda: FakePriceQueryService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


async def test_get_all_prices_requires_ticker(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices")
    assert response.status_code == 422


async def test_get_all_prices(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices", params={"ticker": "btc_usd"})
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_latest_price(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices/latest", params={"ticker": "btc_usd"})
    assert response.status_code == 200
    assert response.json()["timestamp"] == 2000


async def test_get_latest_price_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices/latest", params={"ticker": "eth_usd"})
    assert response.status_code == 404


async def test_get_prices_by_date_filter(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/prices/filter",
        params={"ticker": "btc_usd", "from": 1500, "to": 2500},
    )
    assert response.status_code == 200
    assert [tick["timestamp"] for tick in response.json()] == [2000]


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
