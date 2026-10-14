"""Фабрика приложения Celery.

Приложение Celery собирается из :class:`Settings` и настраивается расписанием,
которое запускает сборщик цен. Функции задач живут в
:mod:`derbit_client.infrastructure.celery.tasks`.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from derbit_client.infrastructure.config import Settings

TASK_FETCH_PRICES = "derbit_client.fetch_index_prices"


def _parse_crontab(expression: str) -> crontab:
    """Разобрать 5-полевое cron-выражение (минута час день месяц день_недели)."""
    parts = expression.split()
    if len(parts) != 5:
        raise ValueError(f"Expected a 5-field cron expression, got: {expression!r}")
    minute, hour, day_of_month, month_of_year, day_of_week = parts
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
    )


def build_celery_app(settings: Settings) -> Celery:
    """Создать и настроить экземпляр приложения Celery."""
    app = Celery("derbit_client")
    app.conf.update(
        broker_url=settings.celery.broker_url,
        result_backend=settings.celery.result_backend,
        timezone=settings.celery.timezone,
        enable_utc=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_acks_late=True,
    )
    app.conf.beat_schedule = {
        "fetch-index-prices": {
            "task": TASK_FETCH_PRICES,
            "schedule": _parse_crontab(settings.celery.fetch_cron),
        }
    }
    return app
