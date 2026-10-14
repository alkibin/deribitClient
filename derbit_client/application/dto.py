"""Data transfer objects returned by application services."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PriceTickDTO:
    """Serializable representation of a stored price tick."""

    ticker: str
    price: Decimal
    timestamp: int
