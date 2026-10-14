"""Фабрика приложения Celery."""

from celery import Celery

from src.core.config import Settings

TASK_FETCH_PRICES = "src.fetch_index_prices"


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
            "schedule": settings.celery.fetch_cron
        }
    }
    return app
