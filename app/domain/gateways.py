from abc import ABC, abstractmethod

from app.domain.entities import IndexPrice


class IndexPriceGateway(ABC):
    """Port for reading the current index price of one instrument."""

    @abstractmethod
    async def get_index_price(self, index_name: str) -> IndexPrice:
        """Return the current index price for an index such as btc_usd."""
