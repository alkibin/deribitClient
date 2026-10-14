"""Тесты слоя репозитория (in-memory SQLite)."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.entities import PriceTick
from src.infrastructure.db.repository import SqlAlchemyPriceRepository


async def test_add_many_and_get_all(session_factory: async_sessionmaker[AsyncSession]) -> None:
    session = session_factory()
    repository = SqlAlchemyPriceRepository(session)
    await repository.add_many(
        [
            PriceTick(ticker="btc_usd", price=Decimal("100"), timestamp=1),
            PriceTick(ticker="btc_usd", price=Decimal("200"), timestamp=2),
        ]
    )
    await session.commit()

    stored = await repository.get_all("btc_usd")
    assert [tick.timestamp for tick in stored] == [1, 2]


async def test_get_latest_returns_most_recent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session = session_factory()
    repository = SqlAlchemyPriceRepository(session)
    await repository.add_many(
        [
            PriceTick(ticker="eth_usd", price=Decimal("10"), timestamp=10),
            PriceTick(ticker="eth_usd", price=Decimal("30"), timestamp=30),
            PriceTick(ticker="eth_usd", price=Decimal("20"), timestamp=20),
        ]
    )
    await session.commit()

    latest = await repository.get_latest("eth_usd")
    assert latest is not None
    assert latest.timestamp == 30
    assert latest.price == Decimal("30")


async def test_get_latest_missing_returns_none(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = SqlAlchemyPriceRepository(session_factory())
    assert await repository.get_latest("btc_usd") is None


async def test_get_between_filters_inclusive(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session = session_factory()
    repository = SqlAlchemyPriceRepository(session)
    await repository.add_many(
        [PriceTick(ticker="btc_usd", price=Decimal(i), timestamp=i) for i in range(1, 6)]
    )
    await session.commit()

    filtered = await repository.get_between("btc_usd", start=2, end=4)
    assert [tick.timestamp for tick in filtered] == [2, 3, 4]


async def test_get_all_paginates(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session = session_factory()
    repository = SqlAlchemyPriceRepository(session)
    await repository.add_many(
        [PriceTick(ticker="btc_usd", price=Decimal(i), timestamp=i) for i in range(1, 6)]
    )
    await session.commit()

    page = await repository.get_all("btc_usd", limit=2, offset=1)
    assert [tick.timestamp for tick in page] == [2, 3]


async def test_count_returns_number_of_ticks(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session = session_factory()
    repository = SqlAlchemyPriceRepository(session)
    await repository.add_many(
        [PriceTick(ticker="btc_usd", price=Decimal(i), timestamp=i) for i in range(1, 6)]
    )
    await session.commit()

    assert await repository.count("btc_usd") == 5
    assert await repository.count("eth_usd") == 0


async def test_count_between_counts_only_range(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session = session_factory()
    repository = SqlAlchemyPriceRepository(session)
    await repository.add_many(
        [PriceTick(ticker="btc_usd", price=Decimal(i), timestamp=i) for i in range(1, 6)]
    )
    await session.commit()

    assert await repository.count_between("btc_usd", start=2, end=4) == 3
    assert await repository.count_between("btc_usd") == 5
