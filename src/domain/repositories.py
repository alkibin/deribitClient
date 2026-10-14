"""Контракт репозитория для сохранения и чтения сущностей."""

from abc import ABC, abstractmethod

from src.domain.entities import PriceTick


class PriceRepository(ABC):
    """Абстрактный класс доступа к сохранённым ценовым тикам."""

    @abstractmethod
    async def add_many(self, ticks: list[PriceTick]) -> None:
        """Сохранить батч ценовых тиков в одной транзакции."""

    @abstractmethod
    async def get_all(self, ticker: str) -> list[PriceTick]:
        """Вернуть все сохранённые тики для тикера."""

    @abstractmethod
    async def get_latest(self, ticker: str) -> PriceTick | None:
        """Вернуть самый свежий тик для тикера или None, если данных нет."""

    @abstractmethod
    async def get_between(
        self,
        ticker: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[PriceTick]:
        """Вернуть тики для тикера в заданном временном диапазоне."""
