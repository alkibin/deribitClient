"""Тесты асинхронного клиента Deribit на базе aiohttp."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import aiohttp
import pytest

from derbit_client.infrastructure.deribit.client import (
    DeribitClient,
    DeribitClientError,
    DeribitError,
    DeribitNotFoundError,
    DeribitRateLimitError,
    DeribitServerError,
)


class FakeResponse:
    """Минимальная замена ответа aiohttp в виде асинхронного контекстного менеджера."""

    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._payload = payload or {}
        self.status = status
        self.headers = headers or {}

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    """Записывает запросы и возвращает заранее заданную последовательность ответов.

    Если задан один ответ, он переиспользуется; при нескольких ответах они
    выдаются по порядку, что позволяет моделировать повторы. Исключение в
    очереди поднимается при вызове ``get``.
    """

    def __init__(self, *responses: FakeResponse | Exception) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((url, kwargs))
        item = self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]
        if isinstance(item, Exception):
            raise item
        return item


class RecordingSleep:
    """Хук сна, записывающий длительности пауз вместо реального ожидания."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def _build_client(session: FakeSession, **overrides: Any) -> DeribitClient:
    params: dict[str, Any] = {
        "session": session,
        "base_url": "https://example.test/api/v2",
        "timeout": 5,
        "sleep": RecordingSleep(),
    }
    params.update(overrides)
    return DeribitClient(**params)


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


async def test_get_index_price_raises_on_error_payload_without_retry() -> None:
    session = FakeSession(FakeResponse({"error": {"message": "bad ticker"}}))
    client = _build_client(session)

    with pytest.raises(DeribitError):
        await client.get_index_price("unknown")

    assert len(session.calls) == 1


async def test_get_index_price_raises_on_unexpected_payload() -> None:
    session = FakeSession(FakeResponse({"result": {}}))
    client = _build_client(session)

    with pytest.raises(DeribitError):
        await client.get_index_price("btc_usd")


async def test_get_index_price_raises_not_found_without_retry() -> None:
    session = FakeSession(FakeResponse(status=404))
    client = _build_client(session)

    with pytest.raises(DeribitNotFoundError):
        await client.get_index_price("btc_usd")

    assert len(session.calls) == 1


async def test_get_index_price_raises_client_error_without_retry() -> None:
    session = FakeSession(FakeResponse(status=400))
    client = _build_client(session)

    with pytest.raises(DeribitClientError):
        await client.get_index_price("btc_usd")

    assert len(session.calls) == 1


async def test_get_index_price_retries_server_errors_then_raises() -> None:
    session = FakeSession(FakeResponse(status=503))
    client = _build_client(session, max_retries=2)

    with pytest.raises(DeribitServerError):
        await client.get_index_price("btc_usd")

    assert len(session.calls) == 3


async def test_get_index_price_recovers_after_transient_error() -> None:
    session = FakeSession(
        FakeResponse(status=503),
        FakeResponse({"result": {"index_price": 42}}),
    )
    client = _build_client(session, max_retries=2)

    price = await client.get_index_price("btc_usd")

    assert price == Decimal("42")
    assert len(session.calls) == 2


async def test_get_index_price_honours_retry_after_header() -> None:
    sleep = RecordingSleep()
    session = FakeSession(FakeResponse(status=429, headers={"Retry-After": "2"}))
    client = _build_client(session, max_retries=1, sleep=sleep)

    with pytest.raises(DeribitRateLimitError):
        await client.get_index_price("btc_usd")

    assert sleep.delays == [2.0]


async def test_get_index_price_retries_network_errors() -> None:
    session = FakeSession(
        aiohttp.ClientConnectionError("boom"),
        FakeResponse({"result": {"index_price": 7}}),
    )
    client = _build_client(session, max_retries=1)

    price = await client.get_index_price("btc_usd")

    assert price == Decimal("7")
    assert len(session.calls) == 2


async def test_get_index_price_wraps_exhausted_network_error() -> None:
    session = FakeSession(aiohttp.ClientConnectionError("boom"))
    client = _build_client(session, max_retries=1)

    with pytest.raises(DeribitError):
        await client.get_index_price("btc_usd")

    assert len(session.calls) == 2


async def test_get_index_price_backs_off_between_retries() -> None:
    sleep = RecordingSleep()
    session = FakeSession(FakeResponse(status=503))
    client = _build_client(session, max_retries=2, backoff_max=8.0, sleep=sleep)

    with pytest.raises(DeribitServerError):
        await client.get_index_price("btc_usd")

    assert len(sleep.delays) == 2
    assert all(0.0 <= delay <= 9.0 for delay in sleep.delays)


def test_parse_retry_after_ignores_invalid_values() -> None:
    assert DeribitClient._parse_retry_after(None) is None
    assert DeribitClient._parse_retry_after("abc") is None
    assert DeribitClient._parse_retry_after("-3") == 0.0
