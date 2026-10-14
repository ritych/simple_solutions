from datetime import date
from decimal import Decimal

import pytest

from app.application.price_query import PriceQueryService
from app.domain.entities import PriceSnapshot, Ticker
from app.domain.exceptions import PriceNotFoundError
from tests.fakes import InMemoryPriceRepository

_DAY = date(2026, 10, 14)
_START = 1_791_936_000
_NEXT_DAY = 1_792_022_400


def _service_with(*snapshots: PriceSnapshot) -> PriceQueryService:
    repository = InMemoryPriceRepository()
    for snapshot in snapshots:
        repository.add(snapshot)
    return PriceQueryService(repository)


def _snapshot(ticker: str, price: str, recorded_at: int) -> PriceSnapshot:
    return PriceSnapshot(ticker=ticker, price=Decimal(price), recorded_at=recorded_at)


def test_list_all_returns_only_the_requested_ticker_in_time_order() -> None:
    service = _service_with(
        _snapshot("btc_usd", "30", _START + 120),
        _snapshot("eth_usd", "2", _START),
        _snapshot("btc_usd", "10", _START),
    )

    values = service.list_all(Ticker("BTC_USD"))

    assert [item.price for item in values] == [Decimal("10"), Decimal("30")]


def test_latest_returns_the_newest_snapshot() -> None:
    service = _service_with(
        _snapshot("btc_usd", "10", _START),
        _snapshot("btc_usd", "30", _START + 60),
    )

    latest = service.latest(Ticker("btc_usd"))

    assert latest.price == Decimal("30")
    assert latest.recorded_at == _START + 60


def test_latest_raises_when_ticker_has_no_rows() -> None:
    service = _service_with()

    with pytest.raises(PriceNotFoundError):
        service.latest(Ticker("btc_usd"))


def test_utc_date_filter_is_half_open_day_boundary() -> None:
    service = _service_with(
        _snapshot("btc_usd", "1", _START - 1),
        _snapshot("btc_usd", "2", _START),
        _snapshot("btc_usd", "3", _NEXT_DAY - 1),
        _snapshot("btc_usd", "4", _NEXT_DAY),
        _snapshot("eth_usd", "9", _START),
    )

    values = service.list_for_utc_date(Ticker("btc_usd"), _DAY)

    assert [item.price for item in values] == [Decimal("2"), Decimal("3")]
