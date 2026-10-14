from celery import Celery

from app.infrastructure.config import Settings


def create_celery(settings: Settings) -> Celery:
    """Build a Celery application. The broker is Redis; task results are not stored."""

    application = Celery("price_tracker", broker=settings.redis_url)
    application.conf.update(
        broker_connection_retry_on_startup=True,
        task_ignore_result=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        beat_schedule={
            "collect-index-prices": {
                "task": "price_tracker.collect_index_prices",
                "schedule": float(settings.price_fetch_interval_seconds),
            }
        },
    )
    return application
