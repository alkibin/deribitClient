"""Контракт репозитория для сохранения и чтения сущностей :class:`PriceTick`.

Интерфейс живёт в доменном слое и не зависит ни от чего, кроме доменной
сущности. Конкретные реализации (например, SQLAlchemy) относятся к
инфраструктуре, что сохраняет направление зависимостей внутрь.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from derbit_client.domain.entities import PriceTick


class PriceRepository(ABC):
    """Абстрактный шлюз доступа к сохранённым ценовым тикам."""

    @abstractmethod
    async def add_many(self, ticks: list[PriceTick]) -> None:
        """Сохранить батч ценовых тиков в одной транзакции."""

    @abstractmethod
    async def get_all(self, ticker: str) -> list[PriceTick]:
        """Вернуть все сохранённые тики для ``ticker`` в порядке возрастания времени."""

    @abstractmethod
    async def get_latest(self, ticker: str) -> PriceTick | None:
        """Вернуть самый свежий тик для ``ticker`` или ``None``, если данных нет."""

    @abstractmethod
    async def get_between(
        self,
        ticker: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[PriceTick]:
        """Вернуть тики для ``ticker`` в диапазоне UNIX timestamp (включительно)."""
