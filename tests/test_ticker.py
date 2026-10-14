import pytest

from app.domain.entities import Ticker
from app.domain.exceptions import InvalidTickerError


def test_ticker_is_normalized() -> None:
    assert Ticker("  BTC_USD  ").value == "btc_usd"


def test_ticker_rejects_values_without_quote() -> None:
    with pytest.raises(InvalidTickerError):
        Ticker("btc")


def test_ticker_rejects_hyphenated_names() -> None:
    with pytest.raises(InvalidTickerError):
        Ticker("btc-usd")


def test_ticker_rejects_empty_value() -> None:
    with pytest.raises(InvalidTickerError):
        Ticker("   ")
