"""Тесты фабрики приложения Celery и регистрации задач."""

from __future__ import annotations

from src.core.config import Settings
from src.infrastructure.celery.app import (
    TASK_FETCH_PRICES,
    build_celery_app,
)


def test_build_celery_app_registers_beat_schedule() -> None:
    settings = Settings()
    app = build_celery_app(settings)

    schedule = app.conf.beat_schedule["fetch-index-prices"]
    assert schedule["task"] == TASK_FETCH_PRICES
    assert schedule["schedule"] == settings.celery.fetch_cron
    assert app.conf.broker_url == settings.celery.broker_url
    assert app.conf.enable_utc is True


def test_fetch_task_is_registered() -> None:
    from src.infrastructure.celery import tasks

    assert TASK_FETCH_PRICES in tasks.celery_app.tasks
