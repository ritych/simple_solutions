from decimal import Decimal

from pydantic import BaseModel

from app.domain.entities import PriceSnapshot


def format_price(price: Decimal) -> str:
    return format(price.normalize(), "f")


class PriceItemResponse(BaseModel):
    ticker: str
    price: str
    timestamp: int

    @classmethod
    def from_snapshot(cls, snapshot: PriceSnapshot) -> "PriceItemResponse":
        return cls(
            ticker=snapshot.ticker,
            price=format_price(snapshot.price),
            timestamp=snapshot.recorded_at,
        )
