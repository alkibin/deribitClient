"""Typed application configuration loaded from environment variables.

All settings are grouped in :class:`Settings`; there are no module-level
mutable globals. Instances are created through cached factory functions so a
single object can be injected where needed while remaining easy to override in
tests.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class DeribitSettings(BaseModel):
    """Connection parameters for the Deribit API."""

    base_url: str = "https://www.deribit.com/api/v2"
    timeout: float = 10.0
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
    """Connection parameters for PostgreSQL."""

    host: str = "localhost"
    port: int = 5432
    user: str = "derbit"
    password: str = "derbit"
    db: str = "derbit"

    def dsn(self, driver: str = "postgresql+asyncpg") -> str:
        """Build an SQLAlchemy DSN for the given async driver."""
        return f"{driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class CelerySettings(BaseModel):
    """Celery broker, backend and schedule configuration."""

    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/1"
    timezone: str = "UTC"
    fetch_cron: str = "* * * * *"


class Settings(BaseSettings):
    """Root configuration aggregating all nested settings groups."""

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
    """Return the process-wide settings instance (cached factory, not a global)."""
    return Settings()
