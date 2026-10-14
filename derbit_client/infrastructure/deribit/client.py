"""Асинхронный клиент Deribit на базе :mod:`aiohttp`.

Используется только публичный, не требующий авторизации, эндпоинт
``public/get_index_price`` для чтения индексной цены валюты (например,
``btc_usd``). :class:`DeribitClient` структурно реализует порт приложения
:class:`derbit_client.application.ports.IndexPriceProvider`.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

import aiohttp

SleepFunction = Callable[[float], Awaitable[None]]


class DeribitError(RuntimeError):
    """Базовое исключение клиента Deribit."""


class DeribitNotFoundError(DeribitError):
    """Запрошенный ресурс не найден (HTTP 404, например неизвестный тикер)."""


class DeribitRateLimitError(DeribitError):
    """Превышен лимит запросов к Deribit (HTTP 429)."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class DeribitServerError(DeribitError):
    """Ошибка на стороне сервера Deribit (HTTP 5xx)."""


class DeribitClientError(DeribitError):
    """Прочие ошибки запроса к Deribit (HTTP 4xx, кроме 404 и 429)."""


class DeribitClient:
    """Конкретная реализация ``IndexPriceProvider`` поверх REST API Deribit.

    Временные сбои (429, 5xx и сетевые ошибки) повторяются с экспоненциальной
    задержкой и джиттером. Постоянные ошибки (404 и прочие 4xx) не повторяются.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        timeout: float,
        *,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        backoff_max: float = 8.0,
        sleep: SleepFunction = asyncio.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._endpoint = "/public/get_index_price"
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._sleep = sleep
        self._rng = rng or random.Random()

    async def get_index_price(self, ticker: str) -> Decimal:
        """Получить индексную цену для ``ticker``, повторяя временные сбои."""
        for attempt in range(self._max_retries + 1):
            try:
                return await self._request_index_price(ticker)
            except (aiohttp.ClientError, TimeoutError) as error:
                if attempt >= self._max_retries:
                    msg = f"Сетевой сбой при запросе к Deribit: {error}"
                    raise DeribitError(msg) from error
                await self._sleep(self._compute_delay(attempt))
            except DeribitError as error:
                if not self._is_retryable(error) or attempt >= self._max_retries:
                    raise
                await self._sleep(self._compute_delay(attempt, error))
        raise DeribitError("Не удалось получить цену с Deribit")

    async def _request_index_price(self, ticker: str) -> Decimal:
        url = f"{self._base_url}{self._endpoint}"
        params = {"index_name": ticker}

        async with self._session.get(url, params=params, timeout=self._timeout) as response:
            self._raise_for_status(response)
            payload = await response.json()

        result = self._extract_result(payload)
        return Decimal(str(result["index_price"]))

    @staticmethod
    def _raise_for_status(response: aiohttp.ClientResponse) -> None:
        status = response.status
        if status < 400:
            return
        if status == 404:
            raise DeribitNotFoundError(f"Ресурс Deribit не найден (HTTP {status})")
        if status == 429:
            raise DeribitRateLimitError(
                "Превышен лимит запросов к Deribit (HTTP 429)",
                retry_after=DeribitClient._parse_retry_after(response.headers.get("Retry-After")),
            )
        if status >= 500:
            raise DeribitServerError(f"Ошибка сервера Deribit (HTTP {status})")
        raise DeribitClientError(f"Ошибка запроса к Deribit (HTTP {status})")

    @staticmethod
    def _extract_result(payload: dict[str, Any]) -> dict[str, Any]:
        if "error" in payload:
            raise DeribitError(str(payload["error"]))
        result = payload.get("result")
        if not isinstance(result, dict) or "index_price" not in result:
            raise DeribitError(f"Неожиданный ответ Deribit: {payload!r}")
        return result

    @staticmethod
    def _is_retryable(error: DeribitError) -> bool:
        return isinstance(error, (DeribitRateLimitError, DeribitServerError))

    def _compute_delay(self, attempt: int, error: DeribitError | None = None) -> float:
        """Вычислить задержку перед повтором: экспоненциальный backoff + джиттер.

        Для ошибки 429 приоритет отдаётся заголовку ``Retry-After``, если он задан.
        Иначе используется «полный джиттер»: случайная задержка в диапазоне
        ``[0, min(backoff_max, backoff_base * 2 ** attempt)]``.
        """
        if isinstance(error, DeribitRateLimitError) and error.retry_after is not None:
            return error.retry_after
        exponential = self._backoff_base * (2**attempt)
        capped = min(self._backoff_max, exponential)
        return self._rng.uniform(0.0, capped)

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            return None
