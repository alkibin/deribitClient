"""Схемы ответов, публикуемые публичным API."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PriceTickSchema(BaseModel):
    """Сериализованный ценовой тик, возвращаемый клиентам API."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    price: Decimal
    timestamp: int
