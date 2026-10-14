from collections.abc import Sequence


class InvalidTickerError(Exception):
    """Raised when a ticker does not match an index name such as btc_usd."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(
            f"Ticker '{ticker}' is invalid. Expected an index name such as btc_usd."
        )


class PriceNotFoundError(Exception):
    """Raised when a ticker has no stored snapshots."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"Price for ticker '{ticker}' was not found.")


class PriceCollectionError(Exception):
    """Raised when a collection run stored nothing."""

    def __init__(self, failed_tickers: Sequence[str]) -> None:
        self.failed_tickers = tuple(failed_tickers)
        if self.failed_tickers:
            message = "Failed to collect index prices for: " + ", ".join(self.failed_tickers)
        else:
            message = "No tickers were configured for collection."
        super().__init__(message)
