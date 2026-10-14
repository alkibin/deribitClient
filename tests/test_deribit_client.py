"""Тесты асинхронного клиента Deribit на базе aiohttp."""

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from src.infrastructure.deribit.client import (
    DeribitClient,
    DeribitClientError,
    DeribitError,
    DeribitNotFoundError,
    DeribitServerError,
)


def response(payload: dict[str, Any] | None = None, status: int = 200) -> MagicMock:
    """Двойник ответа aiohttp: асинхронный контекстный менеджер с ``json()``."""
    response = MagicMock(status=status)
    response.json = AsyncMock(return_value=payload or {})
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


def make(
    *results: MagicMock | Exception,
    max_retries: int = 3
) -> tuple[DeribitClient, MagicMock, AsyncMock]:
    """Клиент с мок-сессией и мок-сном; вернуть (client, session, sleep)."""
    session = MagicMock()
    session.get.side_effect = list(results)
    sleep = AsyncMock()
    client = DeribitClient(
        session=session,
        base_url="https://example.test/api/v2",
        timeout=5,
        max_retries=max_retries,
        sleep=sleep,
    )
    return client, session, sleep


async def test_get_index_price_returns_decimal() -> None:
    client, *_ = make(response({"result": {"index_price": 83417.55}}))

    price = await client.get_index_price("btc_usd")

    assert price == Decimal("83417.55")
    assert isinstance(price, Decimal)


async def test_get_index_price_calls_correct_endpoint() -> None:
    client, session, _ = make(response({"result": {"index_price": 1}}))

    await client.get_index_price("eth_usd")

    args, kwargs = session.get.call_args.args, session.get.call_args.kwargs
    assert args == ("https://example.test/api/v2/public/get_index_price",)
    assert kwargs["params"] == {"index_name": "eth_usd"}


async def test_get_index_price_raises_on_error_payload_without_retry() -> None:
    client, session, _ = make(response({"error": {"message": "bad ticker"}}))

    with pytest.raises(DeribitError):
        await client.get_index_price("unknown")

    session.get.assert_called_once()


async def test_get_index_price_raises_on_unexpected_payload() -> None:
    client, *_ = make(response({"result": {}}))

    with pytest.raises(DeribitError):
        await client.get_index_price("btc_usd")


async def test_get_index_price_raises_not_found_without_retry() -> None:
    client, session, _ = make(response(status=404))

    with pytest.raises(DeribitNotFoundError):
        await client.get_index_price("btc_usd")

    session.get.assert_called_once()


async def test_get_index_price_raises_client_error_without_retry() -> None:
    client, session, _ = make(response(status=400))

    with pytest.raises(DeribitClientError):
        await client.get_index_price("btc_usd")

    session.get.assert_called_once()


async def test_get_index_price_retries_server_errors_then_raises() -> None:
    client, session, sleep = make(
        response(status=503),
        response(status=503),
        response(status=503),
        max_retries=2,
    )

    with pytest.raises(DeribitServerError):
        await client.get_index_price("btc_usd")

    assert session.get.call_count == 3
    assert sleep.await_count == 2


async def test_get_index_price_recovers_after_transient_error() -> None:
    client, session, _ = make(
        response(status=503),
        response({"result": {"index_price": 42}}),
        max_retries=2,
    )

    price = await client.get_index_price("btc_usd")

    assert price == Decimal("42")
    assert session.get.call_count == 2


async def test_get_index_price_retries_network_errors() -> None:
    client, session, _ = make(
        aiohttp.ClientConnectionError("boom"),
        response({"result": {"index_price": 7}}),
        max_retries=1,
    )

    price = await client.get_index_price("btc_usd")

    assert price == Decimal("7")
    assert session.get.call_count == 2
