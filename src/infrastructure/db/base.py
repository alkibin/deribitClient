"""Декларативная база, общая для всех ORM-моделей."""

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс декларативных моделей SQLAlchemy 2.0."""

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
