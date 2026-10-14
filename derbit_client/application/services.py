"""Application services implementing the use cases of the service.

Services depend only on domain abstractions (the repository interface) and on
the price provider contract, so they can be unit-tested with simple fakes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from derbit_client.application.dto import PriceTickDTO
from derbit_client.domain.entities import PriceTick
from derbit_client.domain.repositories import PriceRepository
from derbit_client.infrastructure.deribit.client import IndexPriceProvider


class PriceService:
    """Coordinates fetching, persisting and reading index prices."""

    def __init__(self, repository: PriceRepository, provider: IndexPriceProvider) -> None:
        self._repository = repository
        self._provider = provider

    async def fetch_and_store(self, tickers: list[str]) -> list[PriceTickDTO]:
        """Fetch the current index price for every ticker and persist it.

        A single UNIX timestamp is captured for the whole batch so that all
        prices collected in one run share the same observation time.
        """
        observed_at = int(datetime.now(tz=UTC).timestamp())
        ticks: list[PriceTick] = []

        for ticker in tickers:
            price = await self._provider.get_index_price(ticker)
            ticks.append(self._build_tick(ticker, price, observed_at))

        await self._repository.add_many(ticks)
        return [self._to_dto(tick) for tick in ticks]

    async def get_all_prices(self, ticker: str) -> list[PriceTickDTO]:
        """Return every stored price for ``ticker``."""
        ticks = await self._repository.get_all(ticker)
        return [self._to_dto(tick) for tick in ticks]

    async def get_latest_price(self, ticker: str) -> PriceTickDTO | None:
        """Return the most recent stored price for ``ticker``."""
        tick = await self._repository.get_latest(ticker)
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
        ticks = await self._repository.get_between(ticker, start, end)
        return [self._to_dto(tick) for tick in ticks]

    @staticmethod
    def _build_tick(ticker: str, price: Decimal, timestamp: int) -> PriceTick:
        return PriceTick(ticker=ticker, price=price, timestamp=timestamp)

    @staticmethod
    def _to_dto(tick: PriceTick) -> PriceTickDTO:
        return PriceTickDTO(ticker=tick.ticker, price=tick.price, timestamp=tick.timestamp)
