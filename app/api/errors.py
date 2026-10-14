from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import InvalidTickerError, PriceNotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidTickerError)
    def handle_invalid_ticker(_request: Request, exc: InvalidTickerError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(PriceNotFoundError)
    def handle_missing_price(_request: Request, exc: PriceNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
