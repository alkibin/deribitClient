"""Фабрика приложения Celery."""

from celery import Celery
from celery.schedules import crontab

from src.core.config import Settings

TASK_FETCH_PRICES = "src.fetch_index_prices"


def _parse_crontab(expression: str) -> crontab:
    """Преобразовать 5-полевое cron-выражение в объект расписания Celery."""
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError(f"Expected a 5-field crontab expression, got: {expression!r}")
    minute, hour, day_of_month, month_of_year, day_of_week = fields
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
    )


def build_celery_app(settings: Settings) -> Celery:
    """Создать и настроить экземпляр приложения Celery."""
    app = Celery("src")
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
