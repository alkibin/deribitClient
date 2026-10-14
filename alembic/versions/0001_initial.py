"""create price_ticks table

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-14

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "price_ticks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("price", sa.Numeric(precision=28, scale=8), nullable=False),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_price_ticks_ticker_timestamp",
        "price_ticks",
        ["ticker", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_price_ticks_ticker_timestamp", table_name="price_ticks")
    op.drop_table("price_ticks")
