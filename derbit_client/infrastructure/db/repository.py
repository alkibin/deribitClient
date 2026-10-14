"""SQLAlchemy implementation of the price repository contracts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from derbit_client.domain.entities import PriceTick
from derbit_client.domain.repositories import PriceReader, PriceWriter
from derbit_client.infrastructure.db.models import PriceTickModel


class SqlAlchemyPriceRepository(PriceReader, PriceWriter):
    """Persists and queries price ticks using an async SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, ticks: list[PriceTick]) -> None:
        models = [self._to_model(tick) for tick in ticks]
        self._session.add_all(models)
        await self._session.flush()

    async def get_all(self, ticker: str) -> list[PriceTick]:
        statement = (
            select(PriceTickModel)
            .where(PriceTickModel.ticker == ticker)
            .order_by(PriceTickModel.timestamp.asc())
        )
        rows = (await self._session.scalars(statement)).all()
        return [self._to_entity(row) for row in rows]

    async def get_latest(self, ticker: str) -> PriceTick | None:
        statement = (
            select(PriceTickModel)
            .where(PriceTickModel.ticker == ticker)
            .order_by(PriceTickModel.timestamp.desc())
            .limit(1)
        )
        row = await self._session.scalar(statement)
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

        rows = (await self._session.scalars(statement)).all()
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
