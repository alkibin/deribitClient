"""Типизированная конфигурация приложения, загружаемая из переменных окружения.

Все настройки сгруппированы в :class:`Settings`; модульных изменяемых глобальных
переменных нет. Экземпляры создаются через кэшированные фабрики, поэтому один
объект можно внедрять куда нужно, а в тестах легко переопределять.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class DeribitSettings(BaseModel):
    """Параметры подключения к API Deribit."""

    base_url: str = "https://www.deribit.com/api/v2"
    timeout: float = 10.0
    max_retries: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 8.0
    # NoDecode keeps the raw env string so it can be parsed as a comma-separated
    # list, matching .env / docker-compose (e.g. "btc_usd,eth_usd").
    tickers: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["btc_usd", "eth_usd"])

    @field_validator("tickers", mode="before")
    @classmethod
    def _split_tickers(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class PostgresSettings(BaseModel):
    """Параметры подключения к PostgreSQL."""

    host: str = "localhost"
    port: int = 5432
    user: str = "derbit"
    password: str = "derbit"
    db: str = "derbit"

    def dsn(self, driver: str = "postgresql+asyncpg") -> str:
        """Собрать DSN SQLAlchemy для указанного асинхронного драйвера."""
        return f"{driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class CelerySettings(BaseModel):
    """Настройки брокера, бэкенда и расписания Celery."""

    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/1"
    timezone: str = "UTC"
    fetch_cron: str = "* * * * *"


class Settings(BaseSettings):
    """Корневая конфигурация, агрегирующая все вложенные группы настроек."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    deribit: DeribitSettings = Field(default_factory=DeribitSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Вернуть общепроцессный экземпляр настроек (кэшированная фабрика, не глобал)."""
    return Settings()
