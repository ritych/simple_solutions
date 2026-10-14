from abc import ABC, abstractmethod

from app.domain.entities import PriceSnapshot


class PriceRepository(ABC):
    """Port for stored price observations."""

    @abstractmethod
    def add(self, snapshot: PriceSnapshot) -> None:
        """Insert a snapshot. The same ticker and timestamp updates the price."""

    @abstractmethod
    def list_by_ticker(self, ticker: str) -> list[PriceSnapshot]:
        """Return every snapshot of the ticker, oldest first."""

    @abstractmethod
    def get_latest(self, ticker: str) -> PriceSnapshot | None:
        """Return the newest snapshot, or None when the ticker has no rows."""

    @abstractmethod
    def list_by_ticker_between(
        self,
        ticker: str,
        start_inclusive: int,
        end_exclusive: int,
    ) -> list[PriceSnapshot]:
        """Return snapshots in [start_inclusive, end_exclusive), oldest first."""
