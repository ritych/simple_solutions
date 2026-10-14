import pytest
from pydantic import ValidationError

from app.infrastructure.config import Settings


def test_tracked_tickers_are_split_and_normalized() -> None:
    settings = Settings(tracked_tickers="BTC_USD, eth_usd")

    assert settings.tracked_ticker_list() == ("btc_usd", "eth_usd")


def test_empty_ticker_list_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(tracked_tickers=" , ")


def test_invalid_ticker_in_settings_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(tracked_tickers="btc_usd,btc")


def test_interval_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(price_fetch_interval_seconds=0)
