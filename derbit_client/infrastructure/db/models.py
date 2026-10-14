"""SQLAlchemy ORM models."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from derbit_client.infrastructure.db.base import Base


class PriceTickModel(Base):
    """Stored index price observation."""

    __tablename__ = "price_ticks"

    # BigInteger on PostgreSQL, Integer on SQLite (used by the test suite) so the
    # auto-incrementing primary key works on both dialects.
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        Index("ix_price_ticks_ticker_timestamp", "ticker", "timestamp"),
    )
