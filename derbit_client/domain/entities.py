"""Domain entity describing a single price observation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PriceTick:
    """An immutable index price observation for a given ticker.

    The ``timestamp`` is stored as a UNIX timestamp (seconds, UTC) because it
    is timezone-agnostic, compact and easy to filter on at the database level.
    """

    ticker: str
    price: Decimal
    timestamp: int

    def __post_init__(self) -> None:
        if not self.ticker:
            raise ValueError("ticker must not be empty")
        if self.timestamp < 0:
            raise ValueError("timestamp must be a non-negative UNIX timestamp")
