"""Tests for the aiohttp-based Deribit client."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from derbit_client.infrastructure.deribit.client import DeribitClient, DeribitError


class FakeResponse:
    """Minimal async-context-manager stand-in for an aiohttp response."""

    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self._payload = payload
        self.status = status

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise DeribitError(f"HTTP {self.status}")

    async def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    """Records requests and returns a preconfigured response."""

    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((url, kwargs))
        return self._response


def _build_client(session: FakeSession) -> DeribitClient:
    return DeribitClient(session=session, base_url="https://example.test/api/v2", timeout=5)


async def test_get_index_price_returns_decimal() -> None:
    session = FakeSession(FakeResponse({"result": {"index_price": 83417.55}}))
    client = _build_client(session)

    price = await client.get_index_price("btc_usd")

    assert price == Decimal("83417.55")
    assert isinstance(price, Decimal)


async def test_get_index_price_calls_correct_endpoint() -> None:
    session = FakeSession(FakeResponse({"result": {"index_price": 1}}))
    client = _build_client(session)

    await client.get_index_price("eth_usd")

    url, kwargs = session.calls[0]
    assert url == "https://example.test/api/v2/public/get_index_price"
    assert kwargs["params"] == {"index_name": "eth_usd"}


async def test_get_index_price_raises_on_error_payload() -> None:
    session = FakeSession(FakeResponse({"error": {"message": "bad ticker"}}))
    client = _build_client(session)

    with pytest.raises(DeribitError):
        await client.get_index_price("unknown")


async def test_get_index_price_raises_on_unexpected_payload() -> None:
    session = FakeSession(FakeResponse({"result": {}}))
    client = _build_client(session)

    with pytest.raises(DeribitError):
        await client.get_index_price("btc_usd")


async def test_get_index_price_propagates_http_errors() -> None:
    session = FakeSession(FakeResponse({}, status=500))
    client = _build_client(session)

    with pytest.raises(DeribitError):
        await client.get_index_price("btc_usd")
