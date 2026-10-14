"""Application service serving read requests for stored index prices.

This is a read-only use case invoked by the HTTP interface. It depends solely
on the :class:`PriceReader` repository contract and returns
:class:`PriceTickDTO` objects to the presentation layer.
"""

from __future__ import annotations

from derbit_client.application.dto import PriceTickDTO
from derbit_client.domain.entities import PriceTick
from derbit_client.domain.repositories import PriceReader


class PriceQueryService:
    """Reads stored index prices on behalf of API clients."""

    def __init__(self, reader: PriceReader) -> None:
        self._reader = reader

    async def get_all_prices(self, ticker: str) -> list[PriceTickDTO]:
        """Return every stored price for ``ticker``."""
        ticks = await self._reader.get_all(ticker)
        return [self._to_dto(tick) for tick in ticks]

    async def get_latest_price(self, ticker: str) -> PriceTickDTO | None:
        """Return the most recent stored price for ``ticker``."""
        tick = await self._reader.get_latest(ticker)
        return self._to_dto(tick) if tick is not None else None

    async def get_prices_between(
        self,
        ticker: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[PriceTickDTO]:
        """Return stored prices for ``ticker`` within an inclusive range."""
        if start is not None and end is not None and start > end:
            raise ValueError("'from' must be less than or equal to 'to'")
        ticks = await self._reader.get_between(ticker, start, end)
        return [self._to_dto(tick) for tick in ticks]

    @staticmethod
    def _to_dto(tick: PriceTick) -> PriceTickDTO:
        return PriceTickDTO(ticker=tick.ticker, price=tick.price, timestamp=tick.timestamp)
