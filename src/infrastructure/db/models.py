"""ORM-модели SQLAlchemy."""

from decimal import Decimal

from sqlalchemy import BigInteger, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class PriceTickModel(Base):
    """Сохранённое наблюдение индексной цены."""

    __tablename__ = "price_ticks"

    ticker: Mapped[str] = mapped_column(String(32))
    price: Mapped[Decimal] = mapped_column(Numeric(28, 8))
    timestamp: Mapped[int]

    __table_args__ = (Index("ix_price_ticks_ticker_timestamp", "ticker", "timestamp"),)
