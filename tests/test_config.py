"""Tests for configuration loading and helpers."""

from __future__ import annotations

from derbit_client.infrastructure.config import (
    CelerySettings,
    PostgresSettings,
    Settings,
)


def test_postgres_dsn_default_driver() -> None:
    settings = PostgresSettings(host="db", port=5433, user="u", password="p", db="name")
    assert settings.dsn() == "postgresql+asyncpg://u:p@db:5433/name"


def test_postgres_dsn_sync_driver() -> None:
    settings = PostgresSettings(host="db", user="u", password="p", db="name")
    assert settings.dsn("postgresql") == "postgresql://u:p@db:5432/name"


def test_settings_parse_nested_env(monkeypatch) -> None:
    monkeypatch.setenv("DERIBIT__TICKERS", "btc_usd,eth_usd,btc_usd")
    monkeypatch.setenv("POSTGRES__PORT", "6543")
    monkeypatch.setenv("CELERY__FETCH_CRON", "*/5 * * * *")

    settings = Settings()

    assert settings.deribit.tickers == ["btc_usd", "eth_usd", "btc_usd"]
    assert settings.postgres.port == 6543
    assert settings.celery.fetch_cron == "*/5 * * * *"


def test_settings_defaults(monkeypatch) -> None:
    for key in ("DERIBIT__TICKERS", "POSTGRES__PORT", "CELERY__FETCH_CRON"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings()

    assert settings.deribit.tickers == ["btc_usd", "eth_usd"]
    assert settings.celery == CelerySettings()
