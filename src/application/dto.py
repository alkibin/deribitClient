"""Объекты передачи данных (DTO), возвращаемые сервисами уровня application."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PriceTickDTO:
    """Сериализуемое представление сохранённого ценового тика."""

    ticker: str
    price: Decimal
    timestamp: int


@dataclass(frozen=True, slots=True)
class Page[T]:
    """Страница результатов постраничной выборки."""

    items: list[T]
    total: int
    limit: int
    offset: int
