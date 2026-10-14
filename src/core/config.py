"""Типизированная конфигурация приложения, загружаемая из переменных окружения."""

from functools import lru_cache
from typing import Annotated

from celery.worker.strategy import proto1_to_proto2
from pydantic import Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class DeribitSettings(BaseSettings):
    """Параметры подключения к API Deribit."""

    base_url: str = "https://www.deribit.com/api/v2"
    timeout: float = 10.0
    max_retries: int = 3

    tickers: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["btc_usd", "eth_usd"])


class PostgresSettings(BaseSettings):
    """Параметры подключения к PostgreSQL."""

    host: str = "localhost"
    port: int = 5432
    user: str = "derbit"
    password: str = "derbit"
    db: str = "derbit"

    @property
    def dsn(self, driver: str = "postgresql+asyncpg") -> str:
        return f"{driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class CelerySettings(BaseSettings):
    """Настройки брокера, бэкенда и расписания Celery."""

    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/1"
    timezone: str = "UTC"
    fetch_cron: str = "* * * * *"



class Settings(BaseSettings):
    """Корневая конфигурация, агрегирующая все вложенные группы настроек."""

    deribit: DeribitSettings = Field(default_factory=DeribitSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Вернуть общепроцессный экземпляр настроек (кэшированная фабрика, не глобал)."""
    return Settings()
