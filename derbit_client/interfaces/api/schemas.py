"""Response schemas exposed by the public API."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PriceTickSchema(BaseModel):
    """Serialized price tick returned to API clients."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    price: Decimal
    timestamp: int
