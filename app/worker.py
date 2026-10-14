from celery import Celery

from app.domain.exceptions import PriceCollectionError
from app.infrastructure.celery_factory import create_celery
from app.infrastructure.collect_job import CollectIndexPricesJob
from app.infrastructure.config import Settings


def create_worker() -> Celery:
    """Register the collection task on a Celery application built from the environment."""

    settings = Settings.from_env()
    application = create_celery(settings)

    @application.task(
        name="price_tracker.collect_index_prices",
        autoretry_for=(PriceCollectionError,),
        retry_backoff=True,
        retry_jitter=True,
        max_retries=3,
    )
    def collect_index_prices() -> dict[str, object]:
        return CollectIndexPricesJob(Settings.from_env()).execute()

    return application


# Celery's loader imports this object. It is the worker entrypoint, not shared business state.
celery_app = create_worker()
