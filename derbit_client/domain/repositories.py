"""Repository contracts for persisting and querying :class:`PriceTick` entities.

The interfaces live in the domain layer and depend on nothing but the domain
entity. They are segregated by intent (write vs read) so that an application
service depends only on the operations it actually uses. Concrete
implementations (e.g. SQLAlchemy) belong to infrastructure, which keeps the
dependency direction pointing inwards.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from derbit_client.domain.entities import PriceTick


class PriceWriter(ABC):
    """Write-side persistence gateway for price ticks."""

    @abstractmethod
    async def add_many(self, ticks: list[PriceTick]) -> None:
        """Persist a batch of price ticks in a single transaction."""


class PriceReader(ABC):
    """Read-side persistence gateway for price ticks."""

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
