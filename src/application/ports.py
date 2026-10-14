"""Исходящие порты (абстракции, от которых зависит слой application)."""

from decimal import Decimal
from typing import Protocol


class IndexPriceProvider(Protocol):
    """Порт, описывающий способ получения индексной цены приложением."""

    async def get_index_price(self, ticker: str) -> Decimal:
        """Вернуть текущую индексную цену для ``ticker`` (например, ``btc_usd``)."""
