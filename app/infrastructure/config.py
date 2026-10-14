from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.entities import Ticker
from app.domain.exceptions import InvalidTickerError


class Settings(BaseSettings):
    """Process configuration loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://price:price@localhost:5432/prices"
    redis_url: str = "redis://localhost:6379/0"
    deribit_base_url: str = "https://www.deribit.com/api/v2"
    tracked_tickers: str = "btc_usd,eth_usd"
    http_timeout_seconds: float = Field(default=10, gt=0)
    price_fetch_interval_seconds: int = Field(default=60, ge=1)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls()

    @field_validator("tracked_tickers")
    @classmethod
    def check_tracked_tickers(cls, value: str) -> str:
        parts = [item.strip() for item in value.split(",") if item.strip()]
        if not parts:
            raise ValueError("TRACKED_TICKERS must contain at least one ticker.")
        for part in parts:
            try:
                Ticker(part)
            except InvalidTickerError as exc:
                raise ValueError(str(exc)) from exc
        return value

    def tracked_ticker_list(self) -> tuple[str, ...]:
        return tuple(
            Ticker(item).value for item in self.tracked_tickers.split(",") if item.strip()
        )
