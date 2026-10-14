"""Outbound ports (abstractions the application depends on).

Ports are owned by the application layer and implemented by infrastructure, so
dependencies point inwards. This keeps application services free of any import
from :mod:`derbit_client.infrastructure`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol


class IndexPriceProvider(Protocol):
    """Port describing how the application obtains an index price."""

    async def get_index_price(self, ticker: str) -> Decimal:
        """Return the current index price for ``ticker`` (e.g. ``btc_usd``)."""
        ...
