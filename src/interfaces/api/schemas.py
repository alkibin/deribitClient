"""Схемы запросов и ответов, публикуемые публичным API."""

from __future__ import annotations

from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PriceTickSchema(BaseModel):
    """Сериализованный ценовой тик, возвращаемый клиентам API."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    price: Decimal
    timestamp: int


class PriceFilterSchema(BaseModel):
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
        # Проверяем зависимость полей: from <= to
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("'from' must be less than or equal to 'to'")
        return self
