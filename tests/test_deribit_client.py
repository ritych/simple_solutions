import asyncio
from decimal import Decimal

import pytest

from app.infrastructure.deribit import DeribitClientError, DeribitIndexPriceClient

_SUCCESS_BODY = """
{
  "jsonrpc": "2.0",
  "result": {
    "estimated_delivery_price": 63950.5,
    "index_price": 63948.12
  },
  "usIn": 1,
  "usOut": 2,
  "usDiff": 1,
  "testnet": false
}
"""


class _FakeResponse:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self._body = body

    async def text(self) -> str:
        return self._body

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.urls: list[str] = []
        self.params: list[dict[str, str]] = []

    def get(self, url: str, *, params: dict[str, str]) -> _FakeResponse:
        self.urls.append(url)
        self.params.append(dict(params))
        return self._response

    async def close(self) -> None:
        return None


def _read(body: str, status: int = 200, index_name: str = "btc_usd") -> object:
    session = _FakeSession(_FakeResponse(status, body))
    client = DeribitIndexPriceClient(
        "https://www.deribit.com/api/v2/",
        timeout_seconds=5,
        session=session,
    )

    async def request() -> object:
        async with client:
            return await client.get_index_price(index_name), session

    return asyncio.run(request())


def test_client_reads_index_price_and_request_url() -> None:
    quote, session = _read(_SUCCESS_BODY)

    assert quote.price == Decimal("63948.12")
    assert quote.name == "btc_usd"
    assert session.urls == ["https://www.deribit.com/api/v2/public/get_index_price"]
    assert session.params == [{"index_name": "btc_usd"}]


def test_client_accepts_matching_name_when_exchange_sends_it() -> None:
    body = '{"result":{"index_price":10.5,"name":"btc_usd"}}'
    quote, _session = _read(body)
    assert quote.name == "btc_usd"
    assert quote.price == Decimal("10.5")


def test_client_rejects_http_error() -> None:
    with pytest.raises(DeribitClientError, match="HTTP 503"):
        _read("unavailable", status=503)


def test_client_rejects_jsonrpc_error() -> None:
    body = '{"jsonrpc":"2.0","error":{"message":"Invalid params","code":-32602}}'
    with pytest.raises(DeribitClientError, match="Invalid params"):
        _read(body)


def test_client_rejects_non_json_body() -> None:
    with pytest.raises(DeribitClientError, match="non-JSON"):
        _read("nope")


def test_client_rejects_non_positive_price() -> None:
    body = '{"result":{"index_price":0,"name":"btc_usd"}}'
    with pytest.raises(DeribitClientError, match="non-positive"):
        _read(body)


def test_client_rejects_mismatched_index_name() -> None:
    body = '{"result":{"index_price":10,"name":"eth_usd"}}'
    with pytest.raises(DeribitClientError, match="eth_usd"):
        _read(body)


def test_client_requires_open_session() -> None:
    client = DeribitIndexPriceClient("https://www.deribit.com/api/v2", timeout_seconds=5)

    async def request() -> None:
        await client.get_index_price("btc_usd")

    with pytest.raises(RuntimeError):
        asyncio.run(request())
