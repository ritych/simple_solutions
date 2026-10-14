import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routers.health import router as health_router
from app.api.routers.prices import router as prices_router
from app.infrastructure.config import Settings
from app.infrastructure.database import Database

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the HTTP application. Uvicorn loads it with --factory."""

    resolved_settings = settings if settings is not None else Settings.from_env()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        database = Database(resolved_settings.database_url)
        application.state.settings = resolved_settings
        application.state.database = database
        logger.info("API started")
        yield
        database.dispose()

    application = FastAPI(
        title="Deribit index prices",
        summary="Read API for index prices collected from Deribit.",
        description=(
            "Внешний API сохранённых index price Deribit. "
            "Цены btc_usd и eth_usd забирает воркер Celery раз в минуту."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(prices_router)
    return application
