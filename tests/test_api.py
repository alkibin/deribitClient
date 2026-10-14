"""Тесты HTTP-слоя на ASGI-transport с фейковым сервисом."""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.dto import Page, PriceTickDTO
from src.interfaces.api.app_factory import create_app
from src.interfaces.api.di import get_query_service


class FakePriceQueryService:
    """Заглушка сервиса, возвращающая заранее заданные DTO для тестов эндпоинтов."""

    def __init__(self) -> None:
        self._data = [
            PriceTickDTO(ticker="btc_usd", price=Decimal("100"), timestamp=1000),
            PriceTickDTO(ticker="btc_usd", price=Decimal("200"), timestamp=2000),
        ]

    def _page(
        self,
        matched: list[PriceTickDTO],
        *,
        limit: int | None,
        offset: int,
    ) -> Page[PriceTickDTO]:
        items = matched[offset:] if limit is None else matched[offset : offset + limit]
        return Page(items=items, total=len(matched), limit=limit, offset=offset)

    async def get_all_prices(
        self, ticker: str, *, limit: int | None = None, offset: int = 0
    ) -> Page[PriceTickDTO]:
        matched = [tick for tick in self._data if tick.ticker == ticker]
        return self._page(matched, limit=limit, offset=offset)

    async def get_latest_price(self, ticker: str) -> PriceTickDTO | None:
        matching = [tick for tick in self._data if tick.ticker == ticker]
        return matching[-1] if matching else None

    async def get_prices_between(
        self,
        ticker: str,
        *,
        start: int | None = None,
        end: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[PriceTickDTO]:
        matched = [
            tick
            for tick in self._data
            if tick.ticker == ticker
            and (start is None or tick.timestamp >= start)
            and (end is None or tick.timestamp <= end)
        ]
        return self._page(matched, limit=limit, offset=offset)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_query_service] = lambda: FakePriceQueryService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


async def test_get_all_prices_returns_page(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    body = response.json()
    assert [tick["timestamp"] for tick in body["items"]] == [1000, 2000]
    assert body["total"] == 2
    assert body["limit"] == 100
    assert body["offset"] == 0


async def test_get_all_prices_paginates(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/prices",
        params={"ticker": "btc_usd", "limit": 1, "offset": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert [tick["timestamp"] for tick in body["items"]] == [2000]
    assert body["total"] == 2
    assert (body["limit"], body["offset"]) == (1, 1)


async def test_get_all_prices_rejects_limit_above_max(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/prices",
        params={"ticker": "btc_usd", "limit": 100000},
    )
    assert response.status_code == 422


async def test_get_all_prices_requires_ticker(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices")
    assert response.status_code == 422


async def test_get_latest_price(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices/latest", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    assert response.json()["timestamp"] == 2000


async def test_get_latest_price_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices/latest", params={"ticker": "unknown"})

    assert response.status_code == 404
    assert response.json() == {"detail": "No data for ticker 'unknown'"}


async def test_get_prices_by_date_filter(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/prices/filter",
        params={"ticker": "btc_usd", "from": 1500, "to": 2500},
    )

    assert response.status_code == 200
    body = response.json()
    assert [tick["timestamp"] for tick in body["items"]] == [2000]
    assert body["total"] == 1


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
