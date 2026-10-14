from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.domain.entities import PriceSnapshot
from app.domain.repositories import PriceRepository
from app.infrastructure.orm import PriceSnapshotRow


class SqlAlchemyPriceRepository(PriceRepository):
    """PostgreSQL storage for price snapshots."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, snapshot: PriceSnapshot) -> None:
        statement = pg_insert(PriceSnapshotRow).values(
            ticker=snapshot.ticker,
            price=snapshot.price,
            recorded_at=snapshot.recorded_at,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_price_snapshots_ticker_recorded_at",
            set_={"price": statement.excluded.price},
        )
        self._session.execute(statement)

    def list_by_ticker(self, ticker: str) -> list[PriceSnapshot]:
        statement = (
            select(PriceSnapshotRow)
            .where(PriceSnapshotRow.ticker == ticker)
            .order_by(PriceSnapshotRow.recorded_at.asc(), PriceSnapshotRow.id.asc())
        )
        return [self._to_snapshot(row) for row in self._session.scalars(statement)]

    def get_latest(self, ticker: str) -> PriceSnapshot | None:
        statement = (
            select(PriceSnapshotRow)
            .where(PriceSnapshotRow.ticker == ticker)
            .order_by(PriceSnapshotRow.recorded_at.desc(), PriceSnapshotRow.id.desc())
            .limit(1)
        )
        row = self._session.scalars(statement).first()
        if row is None:
            return None
        return self._to_snapshot(row)

    def list_by_ticker_between(
        self,
        ticker: str,
        start_inclusive: int,
        end_exclusive: int,
    ) -> list[PriceSnapshot]:
        statement = (
            select(PriceSnapshotRow)
            .where(
                PriceSnapshotRow.ticker == ticker,
                PriceSnapshotRow.recorded_at >= start_inclusive,
                PriceSnapshotRow.recorded_at < end_exclusive,
            )
            .order_by(PriceSnapshotRow.recorded_at.asc(), PriceSnapshotRow.id.asc())
        )
        return [self._to_snapshot(row) for row in self._session.scalars(statement)]

    def _to_snapshot(self, row: PriceSnapshotRow) -> PriceSnapshot:
        return PriceSnapshot(
            ticker=row.ticker,
            price=row.price,
            recorded_at=row.recorded_at,
        )
