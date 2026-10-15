"""Доменная сущность, описывающая одно наблюдение цены."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PriceTick:
    """Модель данных для слоя бизнес-логики и репозитория."""

    ticker: str
    price: Decimal
    timestamp: int

    def __post_init__(self) -> None:
        if not self.ticker:
            raise ValueError("ticker must not be empty")
        if self.timestamp < 0:
            raise ValueError("timestamp must be a non-negative UNIX timestamp")
        if self.price < 0:
            raise ValueError("price must be a non-negative Decimal")
