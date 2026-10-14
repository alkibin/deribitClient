"""Асинхронный клиент Deribit на базе aiohttp."""

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

import aiohttp
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from .exceptions import (
    DeribitError,
    DeribitNotFoundError,
    DeribitRateLimitError,
    DeribitServerError,
    DeribitClientError,
)

SleepFunction = Callable[[float], Awaitable[None]]


_RETRYABLE_ERRORS = (
    DeribitRateLimitError,
    DeribitServerError,
    aiohttp.ClientError,
    TimeoutError,
)


class DeribitClient:
    """Конкретная реализация ``IndexPriceProvider`` поверх REST API Deribit."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        timeout: float,
        *,
        max_retries: int = 3,
        sleep: SleepFunction = asyncio.sleep,  # свой слип для тестов
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._endpoint = "/public/get_index_price"
        self._max_retries = max_retries
        self._sleep = sleep

    async def get_index_price(self, ticker: str) -> Decimal:
        """Получить индексную цену для ``ticker``, повторяя временные сбои."""
        retryer = AsyncRetrying(
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_random_exponential(),
            retry=retry_if_exception_type(_RETRYABLE_ERRORS),
            sleep=self._sleep,
            reraise=True,
        )
        async for attempt in retryer:
            with attempt:
                return await self._request_index_price(ticker)

    async def _request_index_price(self, ticker: str) -> Decimal:
        url = f"{self._base_url}{self._endpoint}"
        params = {"index_name": ticker}

        async with self._session.get(url, params=params, timeout=self._timeout) as response:
            self._raise_for_status_if_need(response)
            payload = await response.json()

        result = self._extract_result(payload)
        return Decimal(str(result["index_price"]))

    @staticmethod
    def _extract_result(payload: dict[str, Any]) -> dict[str, Any]:
        if "error" in payload:
            raise DeribitError(str(payload["error"]))
        result = payload.get("result")
        if not isinstance(result, dict) or "index_price" not in result:
            raise DeribitError(f"Неожиданный ответ Deribit: {payload!r}")
        return result

    @staticmethod
    def _raise_for_status_if_need(response: aiohttp.ClientResponse) -> None:
        status = response.status
        if status < 400:
            return
        if status == 404:
            raise DeribitNotFoundError(f"Ресурс Deribit не найден (HTTP {status})")
        if status == 429:
            raise DeribitRateLimitError(
                "Превышен лимит запросов к Deribit (HTTP 429)",
            )
        if status >= 500:
            raise DeribitServerError(f"Ошибка сервера Deribit (HTTP {status})")
        raise DeribitClientError(f"Ошибка запроса к Deribit (HTTP {status})")
