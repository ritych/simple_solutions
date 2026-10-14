import re
from dataclasses import dataclass
from decimal import Decimal

from app.domain.exceptions import InvalidTickerError

_TICKER_PATTERN = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")


@dataclass(frozen=True, slots=True)
class Ticker:
    """Index name used by Deribit, for example btc_usd."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if _TICKER_PATTERN.fullmatch(normalized) is None:
            raise InvalidTickerError(self.value)
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, slots=True)
class IndexPrice:
    """A quote returned by the exchange, before it is stored."""

    name: str
    price: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.price, Decimal):
            raise ValueError("Index price must be a Decimal.")
        if self.price <= 0:
            raise ValueError("Index price must be positive.")


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    """One stored observation: ticker, price, and UNIX time in seconds."""

    ticker: str
    price: Decimal
    recorded_at: int

    def __post_init__(self) -> None:
        if not isinstance(self.price, Decimal):
            raise ValueError("Price must be a Decimal.")
        if self.price <= 0:
            raise ValueError("Price must be positive.")
        if isinstance(self.recorded_at, bool) or not isinstance(self.recorded_at, int):
            raise ValueError("Timestamp must be an integer UNIX time.")
        if self.recorded_at < 0:
            raise ValueError("Timestamp must be a non-negative UNIX time.")
