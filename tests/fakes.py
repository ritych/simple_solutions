from collections.abc import Iterable
from decimal import Decimal

from app.domain.clock import Clock
from app.domain.entities import IndexPrice, PriceSnapshot
from app.domain.gateways import IndexPriceGateway
from app.domain.repositories import PriceRepository


class FixedClock(Clock):
    def __init__(self, timestamp: int) -> None:
        self._timestamp = timestamp

    def unix_timestamp(self) -> int:
        return self._timestamp


class InMemoryPriceRepository(PriceRepository):
    def __init__(self) -> None:
        self.snapshots: list[PriceSnapshot] = []

    def add(self, snapshot: PriceSnapshot) -> None:
        self.snapshots = [
            item
            for item in self.snapshots
            if not (item.ticker == snapshot.ticker and item.recorded_at == snapshot.recorded_at)
        ]
        self.snapshots.append(snapshot)

    def list_by_ticker(self, ticker: str) -> list[PriceSnapshot]:
        return self._sorted(item for item in self.snapshots if item.ticker == ticker)

    def get_latest(self, ticker: str) -> PriceSnapshot | None:
        items = self.list_by_ticker(ticker)
        if not items:
            return None
        return items[-1]

    def list_by_ticker_between(
        self,
        ticker: str,
        start_inclusive: int,
        end_exclusive: int,
    ) -> list[PriceSnapshot]:
        return self._sorted(
            item
            for item in self.snapshots
            if item.ticker == ticker and start_inclusive <= item.recorded_at < end_exclusive
        )

    @staticmethod
    def _sorted(items: Iterable[PriceSnapshot]) -> list[PriceSnapshot]:
        return sorted(items, key=lambda item: (item.recorded_at, item.ticker))


class FakeIndexPriceGateway(IndexPriceGateway):
    def __init__(
        self,
        prices: dict[str, Decimal],
        failures: set[str] | None = None,
    ) -> None:
        self._prices = prices
        self._failures = failures or set()
        self.requested: list[str] = []

    async def get_index_price(self, index_name: str) -> IndexPrice:
        self.requested.append(index_name)
        if index_name in self._failures:
            raise RuntimeError(f"gateway failed for {index_name}")
        return IndexPrice(name=index_name, price=self._prices[index_name])
