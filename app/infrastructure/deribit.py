import json
from collections.abc import Mapping
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

import aiohttp

from app.domain.entities import IndexPrice
from app.domain.gateways import IndexPriceGateway

_PRICE_QUANTUM = Decimal("0.00000001")
_USER_AGENT = "deribit-price-tracker/1.0"


class DeribitClientError(Exception):
    """The Deribit HTTP API did not return a usable index price."""


class _HttpResponse(Protocol):
    status: int

    async def text(self) -> str: ...


class _HttpCall(Protocol):
    async def __aenter__(self) -> _HttpResponse: ...

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None: ...


class _HttpSession(Protocol):
    def get(self, url: str, *, params: Mapping[str, str]) -> _HttpCall: ...

    async def close(self) -> None: ...


class DeribitIndexPriceClient(IndexPriceGateway):
    """Reads public index prices from Deribit with aiohttp.

    https://docs.deribit.com/api-reference/market-data/public-get_index_price
    """

    _PATH = "/public/get_index_price"

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        session: _HttpSession | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._session = session
        self._owns_session = False

    async def __aenter__(self) -> "DeribitIndexPriceClient":
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout_seconds),
                headers={"User-Agent": _USER_AGENT},
            )
            self._owns_session = True
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
        self._session = None
        self._owns_session = False

    async def get_index_price(self, index_name: str) -> IndexPrice:
        session = self._session
        if session is None:
            raise RuntimeError("DeribitIndexPriceClient must be entered as an async context manager.")
        url = f"{self._base_url}{self._PATH}"
        async with session.get(url, params={"index_name": index_name}) as response:
            body = await response.text()
            status = response.status
        if status >= 400:
            raise DeribitClientError(f"Deribit HTTP {status}: {body[:300]}")
        return self._parse(index_name, body)

    def _parse(self, index_name: str, body: str) -> IndexPrice:
        try:
            payload = json.loads(body, parse_float=Decimal)
        except json.JSONDecodeError as exc:
            raise DeribitClientError("Deribit returned a non-JSON body.") from exc
        if not isinstance(payload, dict):
            raise DeribitClientError("Deribit returned a JSON value that is not an object.")

        error = payload.get("error")
        if error:
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise DeribitClientError(f"Deribit error: {message}")

        result = payload.get("result")
        if not isinstance(result, dict):
            raise DeribitClientError("Deribit response does not contain result.")

        # The live payload has no result.name. When the field is present, it must
        # match the index we requested so a swapped body is not stored.
        name = result.get("name", index_name)
        if name != index_name:
            raise DeribitClientError(
                f"Deribit returned index '{name}' for requested '{index_name}'."
            )

        try:
            price = _normalize_price(result.get("index_price"))
            return IndexPrice(name=index_name, price=price)
        except ValueError as exc:
            raise DeribitClientError(str(exc)) from exc


def _normalize_price(value: object) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("index_price is missing or has an unexpected type.")
    if isinstance(value, Decimal):
        price = value
    elif isinstance(value, int):
        price = Decimal(value)
    elif isinstance(value, str):
        price = Decimal(value)
    else:
        raise ValueError("index_price has an unexpected type.")

    normalized = price.quantize(_PRICE_QUANTUM, rounding=ROUND_HALF_UP)
    if normalized <= 0:
        raise ValueError("Deribit returned a non-positive index price.")
    return normalized
