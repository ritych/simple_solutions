from types import TracebackType

from sqlalchemy.orm import Session

from app.domain.repositories import PriceRepository
from app.infrastructure.database import Database
from app.infrastructure.price_repository import SqlAlchemyPriceRepository


class SqlAlchemyUnitOfWork:
    """Opens one database transaction and commits it when the block succeeds."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._session: Session | None = None
        self._repository: PriceRepository | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        session = self._database.open_session()
        self._session = session
        self._repository = SqlAlchemyPriceRepository(session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._session
        if session is None:
            return
        try:
            if exc_type is None:
                session.commit()
            else:
                session.rollback()
        finally:
            session.close()
            self._session = None
            self._repository = None

    @property
    def repository(self) -> PriceRepository:
        if self._repository is None:
            raise RuntimeError("Unit of work is not open.")
        return self._repository
