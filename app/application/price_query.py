from datetime import date, datetime, timezone

from app.domain.entities import PriceSnapshot, Ticker
from app.domain.exceptions import PriceNotFoundError
from app.domain.repositories import PriceRepository

_SECONDS_IN_A_DAY = 86_400


class PriceQueryService:
    """Read-side use cases for stored index prices."""

    def __init__(self, repository: PriceRepository) -> None:
        self._repository = repository

    def list_all(self, ticker: Ticker) -> list[PriceSnapshot]:
        return self._repository.list_by_ticker(ticker.value)

    def latest(self, ticker: Ticker) -> PriceSnapshot:
        snapshot = self._repository.get_latest(ticker.value)
        if snapshot is None:
            raise PriceNotFoundError(ticker.value)
        return snapshot

    def list_for_utc_date(self, ticker: Ticker, day: date) -> list[PriceSnapshot]:
        start = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
        return self._repository.list_by_ticker_between(
            ticker.value,
            start_inclusive=start,
            end_exclusive=start + _SECONDS_IN_A_DAY,
        )
