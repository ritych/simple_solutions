from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from app.application.price_query import PriceQueryService
from app.infrastructure.database import Database
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_price_query_service(
    database: Annotated[Database, Depends(get_database)],
) -> Iterator[PriceQueryService]:
    with SqlAlchemyUnitOfWork(database) as unit_of_work:
        yield PriceQueryService(unit_of_work.repository)
