"""Async Deribit client built on top of :mod:`aiohttp`.

Only the public, unauthenticated ``public/get_index_price`` endpoint is used to
read the index price of a currency (e.g. ``btc_usd``). The provider is defined
as a Protocol so that application services can depend on an abstraction instead
of the concrete HTTP client.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol

import aiohttp


class DeribitError(RuntimeError):
    """Raised when Deribit responds with an error payload."""


class IndexPriceProvider(Protocol):
    """Port describing how the application obtains an index price."""

    async def get_index_price(self, ticker: str) -> Decimal:
        """Return the current index price for ``ticker`` (e.g. ``btc_usd``)."""
        ...


class DeribitClient:
    """Concrete :class:`IndexPriceProvider` speaking to the Deribit REST API."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, timeout: float) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._endpoint = "/public/get_index_price"

    async def get_index_price(self, ticker: str) -> Decimal:
        """Fetch the index price for ``ticker`` from Deribit."""
        url = f"{self._base_url}{self._endpoint}"
        params = {"index_name": ticker}

        async with self._session.get(url, params=params, timeout=self._timeout) as response:
            response.raise_for_status()
            payload = await response.json()

        result = self._extract_result(payload)
        return Decimal(str(result["index_price"]))

    @staticmethod
    def _extract_result(payload: dict[str, Any]) -> dict[str, Any]:
        if "error" in payload:
            raise DeribitError(str(payload["error"]))
        result = payload.get("result")
        if not isinstance(result, dict) or "index_price" not in result:
            raise DeribitError(f"Unexpected Deribit response: {payload!r}")
        return result
