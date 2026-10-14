"""Реализация контракта репозитория цен на SQLAlchemy."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import PriceTick
from src.domain.repositories import PriceRepository
from src.infrastructure.db.models import PriceTickModel


class SqlAlchemyPriceRepository(PriceRepository):
    """Сохраняет и читает ценовые тики через асинхронную сессию SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, ticks: list[PriceTick]) -> None:
        models = [self._to_model(tick) for tick in ticks]
        self.session.add_all(models)
        await self.session.flush()

    async def get_all(self, ticker: str) -> list[PriceTick]:
        stmt = (
            select(PriceTickModel)
            .where(PriceTickModel.ticker == ticker)
            .order_by(PriceTickModel.timestamp.asc())
        )
        rows = (await self.session.scalars(stmt))
        return [self._to_entity(row) for row in rows]

    async def get_latest(self, ticker: str) -> PriceTick | None:
        statement = (
            select(PriceTickModel)
            .where(PriceTickModel.ticker == ticker)
            .order_by(PriceTickModel.timestamp.desc())
            .limit(1)
        )
        row = await self.session.scalar(statement)
        return self._to_entity(row) if row is not None else None

    async def get_between(
        self,
        ticker: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[PriceTick]:
        statement = select(PriceTickModel).where(PriceTickModel.ticker == ticker)
        if start is not None:
            statement = statement.where(PriceTickModel.timestamp >= start)
        if end is not None:
            statement = statement.where(PriceTickModel.timestamp <= end)
        statement = statement.order_by(PriceTickModel.timestamp.asc())

        rows = (await self.session.scalars(statement))
        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_model(tick: PriceTick) -> PriceTickModel:
        return PriceTickModel(
            ticker=tick.ticker,
            price=tick.price,
            timestamp=tick.timestamp,
        )

    @staticmethod
    def _to_entity(model: PriceTickModel) -> PriceTick:
        return PriceTick(
            ticker=model.ticker,
            price=model.price,
            timestamp=model.timestamp,
        )
