"""Асинхронный клиент Deribit на базе :mod:`aiohttp`.

Используется только публичный, не требующий авторизации, эндпоинт
``public/get_index_price`` для чтения индексной цены валюты (например,
``btc_usd``). :class:`DeribitClient` структурно реализует порт приложения
:class:`derbit_client.application.ports.IndexPriceProvider`.

Повторы временных сбоев выполняет библиотека :mod:`tenacity`: экспоненциальная
задержка с джиттером, при этом для ошибок 429 приоритет отдаётся заголовку
``Retry-After``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

import aiohttp
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

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


_RETRYABLE_ERRORS: tuple[type[BaseException], ...] = (
    DeribitRateLimitError,
    DeribitServerError,
    aiohttp.ClientError,
    TimeoutError,
)


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
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._endpoint = "/public/get_index_price"
        self._max_retries = max_retries
        self._sleep = sleep
        self._backoff = wait_exponential_jitter(multiplier=backoff_base, max=backoff_max)

    async def get_index_price(self, ticker: str) -> Decimal:
        """Получить индексную цену для ``ticker``, повторяя временные сбои."""
        retryer = AsyncRetrying(
            stop=stop_after_attempt(self._max_retries + 1),
            wait=self._compute_wait,
            retry=retry_if_exception_type(_RETRYABLE_ERRORS),
            retry_error_callback=self._reraise_as_deribit_error,
            sleep=self._sleep,
        )
        async for attempt in retryer:
            with attempt:
                return await self._request_index_price(ticker)
        raise DeribitError("Не удалось получить цену с Deribit")

    async def _request_index_price(self, ticker: str) -> Decimal:
        url = f"{self._base_url}{self._endpoint}"
        params = {"index_name": ticker}

        async with self._session.get(url, params=params, timeout=self._timeout) as response:
            self._raise_for_status(response)
            payload = await response.json()

        result = self._extract_result(payload)
        return Decimal(str(result["index_price"]))

    def _compute_wait(self, retry_state: RetryCallState) -> float:
        """Вернуть задержку перед повтором, уважая заголовок ``Retry-After``.

        Для ошибок 429 с заданным ``Retry-After`` используется значение из
        заголовка, иначе — экспоненциальный backoff с джиттером ``tenacity``.
        """
        outcome = retry_state.outcome
        if outcome is not None:
            exception = outcome.exception()
            if isinstance(exception, DeribitRateLimitError) and exception.retry_after is not None:
                return exception.retry_after
        return self._backoff(retry_state)

    @staticmethod
    def _reraise_as_deribit_error(retry_state: RetryCallState) -> Decimal:
        """Обернуть исчерпавшие повторы сетевые ошибки в :class:`DeribitError`."""
        outcome = retry_state.outcome
        error = outcome.exception() if outcome is not None else None
        if isinstance(error, DeribitError):
            raise error
        raise DeribitError(f"Сетевой сбой при запросе к Deribit: {error}") from error

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
    def _parse_retry_after(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            return None
