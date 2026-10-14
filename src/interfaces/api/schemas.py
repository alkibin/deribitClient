"""Схемы запросов и ответов, публикуемые публичным API."""

from __future__ import annotations

from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


class PriceTickSchema(BaseModel):
    """Сериализованный ценовой тик, возвращаемый клиентам API."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    price: Decimal
    timestamp: int


class PricePageSchema(BaseModel):
    """Постраничный ответ: элементы выборки и метаданные пагинации."""

    model_config = ConfigDict(from_attributes=True)

    items: list[PriceTickSchema]
    total: int
    limit: int
    offset: int


class TickerQuery(BaseModel):
    """Query-параметры с обязательным тикером."""

    ticker: str = Field(
        min_length=1,
        description="Тикер, например 'btc_usd' или 'eth_usd'.",
    )


class PaginationQuery(BaseModel):
    """Query-параметры пагинации выборки."""

    limit: int = Field(
        default=DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Максимум записей в ответе.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Смещение от начала выборки.",
    )


class PriceListQuery(TickerQuery, PaginationQuery):
    """Query-параметры эндпоинта списка сохранённых цен."""


class PriceLatestQuery(TickerQuery):
    """Query-параметры эндпоинта последней цены."""


class PriceFilterQuery(TickerQuery, PaginationQuery):
    """Query-параметры фильтрации цен по диапазону UNIX timestamp."""

    date_from: int | None = Field(
        default=None,
        alias="from",
        ge=0,
        description="Включительная нижняя граница в виде UNIX timestamp (секунды).",
    )
    date_to: int | None = Field(
        default=None,
        alias="to",
        ge=0,
        description="Включительная верхняя граница в виде UNIX timestamp (секунды).",
    )

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        """Проверяем зависимость полей: from <= to."""
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("'from' must be less than or equal to 'to'")
        return self
