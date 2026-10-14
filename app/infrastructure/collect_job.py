import asyncio
import logging

from app.application.ingest_index_prices import CollectionSummary, IngestIndexPrices
from app.domain.clock import Clock, SystemClock
from app.domain.repositories import PriceRepository
from app.infrastructure.config import Settings
from app.infrastructure.database import Database
from app.infrastructure.deribit import DeribitIndexPriceClient
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


class CollectIndexPricesJob:
    """Composition root of one collection run: HTTP client, clock, and database."""

    def __init__(
        self,
        settings: Settings,
        database: Database | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._settings = settings
        self._database = database if database is not None else Database(settings.database_url)
        self._owns_database = database is None
        self._clock = clock if clock is not None else SystemClock()

    def execute(self) -> dict[str, object]:
        try:
            with SqlAlchemyUnitOfWork(self._database) as unit_of_work:
                summary = asyncio.run(self._collect(unit_of_work.repository))
            payload = summary.to_payload()
            logger.info("Saved index prices: %s", payload)
            return payload
        finally:
            if self._owns_database:
                self._database.dispose()

    async def _collect(self, repository: PriceRepository) -> CollectionSummary:
        client = DeribitIndexPriceClient(
            base_url=self._settings.deribit_base_url,
            timeout_seconds=self._settings.http_timeout_seconds,
        )
        async with client:
            use_case = IngestIndexPrices(
                gateway=client,
                repository=repository,
                clock=self._clock,
            )
            return await use_case.execute(self._settings.tracked_ticker_list())
