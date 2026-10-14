"""Контракт репозитория для сохранения и чтения сущностей."""

from abc import ABC, abstractmethod

from src.domain.entities import PriceTick


class PriceRepository(ABC):
    """Абстрактный класс доступа к сохранённым ценовым тикам."""

    @abstractmethod
    async def add_many(self, ticks: list[PriceTick]) -> None:
        """Сохранить батч ценовых тиков в одной транзакции."""

    @abstractmethod
    async def get_all(
        self,
        ticker: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[PriceTick]:
        """Вернуть тики для тикера, начиная с offset и не более limit записей."""

    @abstractmethod
    async def count(self, ticker: str) -> int:
        """Вернуть общее число сохранённых тиков для тикера."""

    @abstractmethod
    async def get_latest(self, ticker: str) -> PriceTick | None:
        """Вернуть самый свежий тик для тикера или None, если данных нет."""

    @abstractmethod
    async def get_between(
        self,
        ticker: str,
        *,
        start: int | None = None,
        end: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[PriceTick]:
        """Вернуть тики для тикера в диапазоне start - end с пагинацией."""

    @abstractmethod
    async def count_between(
        self,
        ticker: str,
        *,
        start: int | None = None,
        end: int | None = None,
    ) -> int:
        """Вернуть число тиков для тикера в заданном временном диапазоне."""
