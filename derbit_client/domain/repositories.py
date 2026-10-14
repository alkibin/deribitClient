"""Repository contract for persisting and querying :class:`PriceTick` entities.

The interface lives in the domain layer and depends on nothing but the domain
entity. Concrete implementations (e.g. SQLAlchemy) belong to infrastructure,
which keeps the dependency direction pointing inwards.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from derbit_client.domain.entities import PriceTick


class PriceRepository(ABC):
    """Abstract persistence gateway for price ticks."""

    @abstractmethod
    async def add_many(self, ticks: list[PriceTick]) -> None:
        """Persist a batch of price ticks in a single transaction."""

    @abstractmethod
    async def get_all(self, ticker: str) -> list[PriceTick]:
        """Return every stored tick for ``ticker`` ordered by time ascending."""

    @abstractmethod
    async def get_latest(self, ticker: str) -> PriceTick | None:
        """Return the most recent tick for ``ticker`` or ``None`` if absent."""

    @abstractmethod
    async def get_between(
        self,
        ticker: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[PriceTick]:
        """Return ticks for ``ticker`` within an inclusive UNIX timestamp range."""
