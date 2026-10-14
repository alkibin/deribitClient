"""Тесты фабрики приложения Celery и регистрации задач."""

from __future__ import annotations

import pytest
from celery.schedules import crontab

from derbit_client.infrastructure.celery.app import (
    TASK_FETCH_PRICES,
    _parse_crontab,
    build_celery_app,
)
from derbit_client.infrastructure.config import Settings


def test_parse_crontab_every_minute() -> None:
    schedule = _parse_crontab("* * * * *")
    assert isinstance(schedule, crontab)


def test_parse_crontab_expression() -> None:
    schedule = _parse_crontab("*/5 3 * * 1")
    assert isinstance(schedule, crontab)


def test_parse_crontab_rejects_invalid_field_count() -> None:
    with pytest.raises(ValueError):
        _parse_crontab("* * *")


def test_build_celery_app_registers_beat_schedule() -> None:
    settings = Settings()
    app = build_celery_app(settings)

    schedule = app.conf.beat_schedule["fetch-index-prices"]
    assert schedule["task"] == TASK_FETCH_PRICES
    assert isinstance(schedule["schedule"], crontab)
    assert app.conf.broker_url == settings.celery.broker_url
    assert app.conf.enable_utc is True


def test_fetch_task_is_registered() -> None:
    from derbit_client.infrastructure.celery import tasks

    assert TASK_FETCH_PRICES in tasks.celery_app.tasks
