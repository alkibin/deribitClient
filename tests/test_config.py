"""Тесты загрузки конфигурации и её хелперов."""

from __future__ import annotations

from src.core.config import (
    CelerySettings,
    PostgresSettings,
    Settings,
)


def test_postgres_dsn_uses_asyncpg_by_default() -> None:
    settings = PostgresSettings(host="db", port=5433, user="u", password="p", db="name")
    assert settings.dsn == "postgresql+asyncpg://u:p@db:5433/name"


def test_settings_ignore_nested_env(monkeypatch) -> None:
    monkeypatch.setenv("DERIBIT__TICKERS", "btc_usd,eth_usd,btc_usd")
    monkeypatch.setenv("POSTGRES__PORT", "6543")
    monkeypatch.setenv("CELERY__FETCH_CRON", "*/5 * * * *")
    monkeypatch.delenv("PORT", raising=False)

    settings = Settings()

    assert settings.deribit.tickers == ["btc_usd", "eth_usd"]
    assert settings.postgres.port == 5432
    assert settings.celery.fetch_cron == "* * * * *"


def test_settings_defaults(monkeypatch) -> None:
    for key in ("DERIBIT__TICKERS", "POSTGRES__PORT", "CELERY__FETCH_CRON"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings()

    assert settings.deribit.tickers == ["btc_usd", "eth_usd"]
    assert settings.celery == CelerySettings()
