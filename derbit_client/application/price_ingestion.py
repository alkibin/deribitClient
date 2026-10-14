"""Application service responsible for ingesting index prices.

This is a write-only use case invoked by the scheduled Celery worker. It depends
solely on the outbound :class:`IndexPriceProvider` port and the
:class:`PriceWriter` repository contract, and knows nothing about the HTTP API.
"""

from __future__ import annotations

from datetime import UTC, datetime

from derbit_client.application.ports import IndexPriceProvider
from derbit_client.domain.entities import PriceTick
from derbit_client.domain.repositories import PriceWriter


class PriceIngestionService:
    """Fetches the current index prices and persists them."""

    def __init__(self, writer: PriceWriter, provider: IndexPriceProvider) -> None:
        self._writer = writer
        self._provider = provider

    async def fetch_and_store(self, tickers: list[str]) -> None:
        """Fetch the current index price for every ticker and persist them.

        A single UNIX timestamp is captured for the whole batch so that all
        prices collected in one run share the same observation time.
        """
        observed_at = int(datetime.now(tz=UTC).timestamp())
        ticks: list[PriceTick] = []
        for ticker in tickers:
            price = await self._provider.get_index_price(ticker)
            ticks.append(PriceTick(ticker=ticker, price=price, timestamp=observed_at))
        await self._writer.add_many(ticks)
