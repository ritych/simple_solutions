from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_price_query_service
from app.api.schemas import PriceItemResponse
from app.application.price_query import PriceQueryService
from app.domain.entities import Ticker

router = APIRouter(prefix="/api/v1", tags=["prices"])


@router.get(
    "/prices",
    response_model=list[PriceItemResponse],
    summary="Все сохранённые цены тикера",
)
def list_prices(
    ticker: Annotated[str, Query(description="Индекс, например btc_usd", examples=["btc_usd"])],
    service: Annotated[PriceQueryService, Depends(get_price_query_service)],
) -> list[PriceItemResponse]:
    snapshots = service.list_all(Ticker(ticker))
    return [PriceItemResponse.from_snapshot(item) for item in snapshots]


@router.get(
    "/prices/latest",
    response_model=PriceItemResponse,
    summary="Последняя сохранённая цена тикера",
    responses={404: {"description": "Для тикера ещё нет ни одной цены"}},
)
def latest_price(
    ticker: Annotated[str, Query(description="Индекс, например btc_usd", examples=["btc_usd"])],
    service: Annotated[PriceQueryService, Depends(get_price_query_service)],
) -> PriceItemResponse:
    return PriceItemResponse.from_snapshot(service.latest(Ticker(ticker)))


@router.get(
    "/prices/by-date",
    response_model=list[PriceItemResponse],
    summary="Цены тикера за календарный день UTC",
)
def prices_by_date(
    ticker: Annotated[str, Query(description="Индекс, например btc_usd", examples=["btc_usd"])],
    date: Annotated[
        date,
        Query(description="Календарный день в UTC, формат YYYY-MM-DD", examples=["2026-10-14"]),
    ],
    service: Annotated[PriceQueryService, Depends(get_price_query_service)],
) -> list[PriceItemResponse]:
    snapshots = service.list_for_utc_date(Ticker(ticker), date)
    return [PriceItemResponse.from_snapshot(item) for item in snapshots]
