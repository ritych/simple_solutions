import asyncio
from decimal import Decimal

import pytest

from app.application.ingest_index_prices import IngestIndexPrices
from app.domain.exceptions import PriceCollectionError
from tests.fakes import FakeIndexPriceGateway, FixedClock, InMemoryPriceRepository

_OBSERVED_AT = 1_791_936_000


def _use_case(
    prices: dict[str, Decimal],
    failures: set[str] | None = None,
) -> tuple[IngestIndexPrices, InMemoryPriceRepository, FakeIndexPriceGateway]:
    repository = InMemoryPriceRepository()
    gateway = FakeIndexPriceGateway(prices, failures)
    use_case = IngestIndexPrices(gateway, repository, FixedClock(_OBSERVED_AT))
    return use_case, repository, gateway


def test_stores_both_tickers_under_one_timestamp() -> None:
    use_case, repository, gateway = _use_case(
        {"btc_usd": Decimal("100.5"), "eth_usd": Decimal("20.25")}
    )

    summary = asyncio.run(use_case.execute(["BTC_USD", "eth_usd"]))

    assert set(gateway.requested) == {"btc_usd", "eth_usd"}
    assert [item.ticker for item in summary.saved] == ["btc_usd", "eth_usd"]
    assert {item.recorded_at for item in summary.saved} == {_OBSERVED_AT}
    assert repository.list_by_ticker("btc_usd")[0].price == Decimal("100.5")
    assert summary.failed_tickers == ()


def test_partial_failure_keeps_the_successful_ticker() -> None:
    use_case, repository, _gateway = _use_case(
        {"btc_usd": Decimal("100.5"), "eth_usd": Decimal("20.25")},
        failures={"eth_usd"},
    )

    summary = asyncio.run(use_case.execute(["btc_usd", "eth_usd"]))

    assert [item.ticker for item in summary.saved] == ["btc_usd"]
    assert summary.failed_tickers == ("eth_usd",)
    assert repository.list_by_ticker("eth_usd") == []


def test_total_failure_stores_nothing_and_raises() -> None:
    use_case, repository, _gateway = _use_case(
        {"btc_usd": Decimal("100.5"), "eth_usd": Decimal("20.25")},
        failures={"btc_usd", "eth_usd"},
    )

    with pytest.raises(PriceCollectionError):
        asyncio.run(use_case.execute(["btc_usd", "eth_usd"]))

    assert repository.snapshots == []


def test_empty_ticker_list_raises() -> None:
    use_case, _repository, _gateway = _use_case({})

    with pytest.raises(PriceCollectionError):
        asyncio.run(use_case.execute([]))
