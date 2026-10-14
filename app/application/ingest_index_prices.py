import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.clock import Clock
from app.domain.entities import PriceSnapshot, Ticker
from app.domain.exceptions import PriceCollectionError
from app.domain.gateways import IndexPriceGateway
from app.domain.repositories import PriceRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CollectionSummary:
    saved: tuple[PriceSnapshot, ...]
    failed_tickers: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "saved": [
                {
                    "ticker": item.ticker,
                    "price": format(item.price, "f"),
                    "timestamp": item.recorded_at,
                }
                for item in self.saved
            ],
            "failed": list(self.failed_tickers),
        }


class IngestIndexPrices:
    """Loads current index prices and stores one snapshot per successful ticker."""

    def __init__(
        self,
        gateway: IndexPriceGateway,
        repository: PriceRepository,
        clock: Clock,
    ) -> None:
        self._gateway = gateway
        self._repository = repository
        self._clock = clock

    async def execute(self, tickers: Sequence[str]) -> CollectionSummary:
        if not tickers:
            raise PriceCollectionError(())

        recorded_at = self._clock.unix_timestamp()
        outcomes = await asyncio.gather(
            *(self._fetch_one(ticker, recorded_at) for ticker in tickers),
            return_exceptions=True,
        )

        saved: list[PriceSnapshot] = []
        failed: list[str] = []
        for ticker, outcome in zip(tickers, outcomes, strict=True):
            if isinstance(outcome, Exception):
                logger.warning("Failed to fetch index price for %s: %s", ticker, outcome)
                failed.append(ticker)
                continue
            self._repository.add(outcome)
            saved.append(outcome)

        if not saved:
            raise PriceCollectionError(tuple(failed))
        return CollectionSummary(saved=tuple(saved), failed_tickers=tuple(failed))

    async def _fetch_one(self, ticker: str, recorded_at: int) -> PriceSnapshot:
        normalized = Ticker(ticker).value
        quote = await self._gateway.get_index_price(normalized)
        return PriceSnapshot(ticker=normalized, price=quote.price, recorded_at=recorded_at)
