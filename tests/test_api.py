from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_price_query_service
from app.api.main import create_app
from app.api.schemas import format_price
from app.application.price_query import PriceQueryService
from app.domain.entities import PriceSnapshot
from app.infrastructure.config import Settings
from tests.fakes import InMemoryPriceRepository

_START = 1_791_936_000


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://price:price@localhost:5432/prices",
        redis_url="redis://localhost:6379/0",
        deribit_base_url="https://www.deribit.com/api/v2",
        tracked_tickers="btc_usd,eth_usd",
        http_timeout_seconds=10,
        price_fetch_interval_seconds=60,
    )


def _snapshot(ticker: str, price: str, recorded_at: int) -> PriceSnapshot:
    return PriceSnapshot(ticker=ticker, price=Decimal(price), recorded_at=recorded_at)


@pytest.fixture
def api() -> tuple[TestClient, InMemoryPriceRepository]:
    repository = InMemoryPriceRepository()
    repository.add(_snapshot("btc_usd", "63948.12000000", _START))
    repository.add(_snapshot("btc_usd", "64000.5", _START + 60))
    repository.add(_snapshot("eth_usd", "2400.25", _START))
    application = create_app(_settings())
    application.dependency_overrides[get_price_query_service] = lambda: PriceQueryService(
        repository
    )
    with TestClient(application) as client:
        yield client, repository


def test_format_price_keeps_exact_decimal_text() -> None:
    assert format_price(Decimal("63948.12000000")) == "63948.12"
    assert format_price(Decimal("10000000000.00")) == "10000000000"


def test_list_prices_returns_only_requested_ticker(api: tuple[TestClient, object]) -> None:
    client, _repository = api

    response = client.get("/api/v1/prices", params={"ticker": "BTC_USD"})

    assert response.status_code == 200
    assert response.json() == [
        {"ticker": "btc_usd", "price": "63948.12", "timestamp": _START},
        {"ticker": "btc_usd", "price": "64000.5", "timestamp": _START + 60},
    ]


def test_latest_price(api: tuple[TestClient, object]) -> None:
    client, _repository = api

    response = client.get("/api/v1/prices/latest", params={"ticker": "eth_usd"})

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "eth_usd",
        "price": "2400.25",
        "timestamp": _START,
    }


def test_latest_price_is_404_when_missing(api: tuple[TestClient, object]) -> None:
    client, _repository = api

    response = client.get("/api/v1/prices/latest", params={"ticker": "sol_usd"})

    assert response.status_code == 404


def test_prices_by_date_uses_utc_day(api: tuple[TestClient, object]) -> None:
    client, repository = api
    repository.add(_snapshot("btc_usd", "1", _START - 1))

    response = client.get(
        "/api/v1/prices/by-date",
        params={"ticker": "btc_usd", "date": "2026-10-14"},
    )

    assert response.status_code == 200
    assert [item["timestamp"] for item in response.json()] == [_START, _START + 60]


def test_prices_by_date_can_be_empty(api: tuple[TestClient, object]) -> None:
    client, _repository = api

    response = client.get(
        "/api/v1/prices/by-date",
        params={"ticker": "btc_usd", "date": "2020-01-01"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_ticker_is_required(api: tuple[TestClient, object]) -> None:
    client, _repository = api

    response = client.get("/api/v1/prices")

    assert response.status_code == 422


def test_invalid_ticker_is_422(api: tuple[TestClient, object]) -> None:
    client, _repository = api

    response = client.get("/api/v1/prices/latest", params={"ticker": "btc"})

    assert response.status_code == 422


def test_invalid_date_is_422(api: tuple[TestClient, object]) -> None:
    client, _repository = api

    response = client.get(
        "/api/v1/prices/by-date",
        params={"ticker": "btc_usd", "date": "14-10-2026"},
    )

    assert response.status_code == 422


def test_health(api: tuple[TestClient, object]) -> None:
    client, _repository = api

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
